# -*- coding: utf-8 -*-
"""政策与公告双维度排雷 — API endpoints 单元测试。

用 TestClient mock AuthMiddleware，覆盖：
- SSE generate_stream（A 股校验 400 / agent 禁用 400 / success 事件序列 / error）
- CRUD 4 端点（list / get / delete / PDF）
- report_id 白名单防路径穿越

不跑真实 LLM/网络/文件系统。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from src.services.policy_minesweeper_service import PolicyMinesweeperInputError


@pytest.fixture
def app():
    """裸 FastAPI（无 AuthMiddleware），挂 policy_minesweeper router。"""
    app = FastAPI()
    from api.v1.endpoints.policy_minesweeper import router

    app.include_router(router)
    return app


@pytest.fixture
def client(app, monkeypatch):
    """TestClient with AuthMiddleware bypassed."""
    # bypass AuthMiddleware + is_agent_available
    monkeypatch.setattr("src.config.Config.is_agent_available", lambda self: True)
    from fastapi.testclient import TestClient

    return TestClient(app)


def _gen_events(*types_and_bodies):
    """生成 SSE data:... 行。"""
    for etype, body in types_and_bodies:
        yield f"data: {json.dumps({'type': etype, **body}, ensure_ascii=False)}\n\n"


# ============================================================
# generate_stream
# ============================================================


class TestGenerateStream:
    def test_malformed_code_returns_422(self, client):
        # Layer 3：Pydantic field_validator 在解析期拦截非 A 股代码（AAPL）→ 422，不进 SSE
        resp = client.post("/generate/stream", json={"stock_code": "AAPL"})
        assert resp.status_code == 422

    def test_empty_code_returns_422(self, client):
        # Layer 3：空代码违反 field_validator → 422
        resp = client.post("/generate/stream", json={"stock_code": ""})
        assert resp.status_code == 422

    def test_sz_suffix_accepted(self, client, monkeypatch):
        """前端 StockAutocomplete 传 canonicalCode 含 .SZ 后缀 → field_validator 归一化为 002617 通过。

        修复回归：原 pattern=^\\d{6}$ 严格化导致 "002617.SZ" 422，本测试验证修复。
        """
        # 模拟 SSE 成功响应（避免真跑 LLM）
        from fastapi.responses import StreamingResponse

        def fake_generate_report(*args, **kwargs):
            kwargs["progress_callback"](
                {
                    "type": "done",
                    "success": True,
                    "report_id": "002617_202607011200",
                    "status": "success",
                    "markdown": "# 露笑科技 002617",
                }
            )
            return {"report_id": "002617_202607011200"}

        monkeypatch.setattr(
            "api.v1.endpoints.policy_minesweeper.policy_minesweeper_service.generate_report",
            fake_generate_report,
        )

        resp = client.post("/generate/stream", json={"stock_code": "002617.SZ"})
        assert resp.status_code == 200
        # 归一化后 002617 应被 service 收到（progress callback 拿到的 code）
        # 这里仅验证端点接受，不深入校验下游

    def test_sh_prefix_accepted(self, client, monkeypatch):
        """前端可能传 ``SH600519`` 前缀格式 → 归一化为 ``600519`` 通过。"""
        from fastapi.responses import StreamingResponse

        def fake_generate_report(*args, **kwargs):
            kwargs["progress_callback"](
                {
                    "type": "done",
                    "success": True,
                    "report_id": "600519_202607011200",
                    "status": "success",
                    "markdown": "# 贵州茅台 600519",
                }
            )
            return {"report_id": "600519_202607011200"}

        monkeypatch.setattr(
            "api.v1.endpoints.policy_minesweeper.policy_minesweeper_service.generate_report",
            fake_generate_report,
        )

        resp = client.post("/generate/stream", json={"stock_code": "SH600519"})
        assert resp.status_code == 200

    def test_bj_suffix_accepted(self, client, monkeypatch):
        """北交所 ``920493.BJ`` 格式归一化为 ``920493`` 通过。"""

        def fake_generate_report(*args, **kwargs):
            kwargs["progress_callback"](
                {
                    "type": "done",
                    "success": True,
                    "report_id": "920493_202607011200",
                    "status": "success",
                    "markdown": "# 北交所 920493",
                }
            )
            return {"report_id": "920493_202607011200"}

        monkeypatch.setattr(
            "api.v1.endpoints.policy_minesweeper.policy_minesweeper_service.generate_report",
            fake_generate_report,
        )

        resp = client.post("/generate/stream", json={"stock_code": "920493.BJ"})
        assert resp.status_code == 200

    def test_whitespace_stripped(self, client, monkeypatch):
        """用户输入 ``  600519  `` 含前后空格 → strip 后归一通过。"""

        def fake_generate_report(*args, **kwargs):
            kwargs["progress_callback"](
                {
                    "type": "done",
                    "success": True,
                    "report_id": "600519_202607011200",
                    "status": "success",
                    "markdown": "# 600519",
                }
            )
            return {"report_id": "600519_202607011200"}

        monkeypatch.setattr(
            "api.v1.endpoints.policy_minesweeper.policy_minesweeper_service.generate_report",
            fake_generate_report,
        )

        resp = client.post("/generate/stream", json={"stock_code": "  600519  "})
        assert resp.status_code == 200

    def test_hk_code_rejected(self, client):
        """港股 ``00700.HK`` 归一后为 ``00700``（5 位）非 A 股 6 位 → 422。"""
        resp = client.post("/generate/stream", json={"stock_code": "00700.HK"})
        assert resp.status_code == 422

    def test_us_code_rejected(self, client):
        """美股 ``AAPL.US`` / ``AAPL`` 归一后非 A 股 6 位 → 422。"""
        resp = client.post("/generate/stream", json={"stock_code": "AAPL.US"})
        assert resp.status_code == 422

    def test_garbage_code_rejected(self, client):
        """无法识别的乱码 → 422。"""
        resp = client.post("/generate/stream", json={"stock_code": "abc!@#"})
        assert resp.status_code == 422

    def test_invalid_horizon_returns_422(self, client):
        # Layer 3：horizon 是 Literal["short","medium","long"]，非法值 → 422
        resp = client.post(
            "/generate/stream", json={"stock_code": "600519", "horizon": "bogus"}
        )
        assert resp.status_code == 422

    def test_agent_disabled_returns_400(self, client, monkeypatch):
        monkeypatch.setattr("src.config.Config.is_agent_available", lambda self: False)
        resp = client.post("/generate/stream", json={"stock_code": "600519"})
        assert resp.status_code == 400

    def test_success_done_event(self, client, monkeypatch):
        def fake_generate(*, raw_code, raw_name, horizon, progress_callback):
            progress_callback(
                {
                    "type": "done",
                    "report_id": "600519_202606261200",
                    "status": "success",
                    "markdown": "# test",
                }
            )
            return {"report_id": "600519_202606261200"}

        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.generate_report",
            fake_generate,
        )
        resp = client.post(
            "/generate/stream",
            json={"stock_code": "600519", "stock_name": "贵州茅台"},
        )
        assert resp.status_code == 200
        payloads = [
            json.loads(line[6:])
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        assert any(p.get("type") == "done" for p in payloads)

    def test_service_error_yields_error_event(self, client, monkeypatch):
        def boom(**_kw):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.generate_report",
            boom,
        )
        resp = client.post("/generate/stream", json={"stock_code": "600519"})
        assert resp.status_code == 200
        payloads = [
            json.loads(line[6:])
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        assert any(p.get("type") == "error" for p in payloads)


# ============================================================
# list_reports
# ============================================================


class TestListReports:
    def _wire(self, monkeypatch, rows=None, total=0):
        svc = MagicMock()
        svc.list_reports.return_value = (rows or [], total)
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.list_reports",
            svc.list_reports,
        )

    def test_empty_list(self, client, monkeypatch):
        self._wire(monkeypatch)
        resp = client.get("/reports")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["data"] == []

    def test_list_items(self, client, monkeypatch):
        self._wire(
            monkeypatch,
            rows=[
                {
                    "id": "600519_202606261200",
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                    "status": "success",
                    "composite_score": -35,
                    "verdict": "中等利空",
                    "confidence": 78,
                }
            ],
            total=1,
        )
        resp = client.get("/reports")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["stock_code"] == "600519"
        assert data[0]["composite_score"] == -35

    def test_list_filter_by_code(self, client, monkeypatch):
        svc = MagicMock()
        svc.list_reports.return_value = ([], 0)
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.list_reports",
            svc.list_reports,
        )
        client.get("/reports?stock_code=600519")
        svc.list_reports.assert_called_once()
        _, kw = svc.list_reports.call_args
        assert kw.get("stock_code") == "600519"


# ============================================================
# get_report
# ============================================================


class TestGetReport:
    def test_missing_returns_404(self, client, monkeypatch):
        svc = MagicMock()
        svc.get_report.return_value = None
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_report",
            svc.get_report,
        )
        resp = client.get("/reports/600519_202606261200")
        assert resp.status_code == 404

    def test_invalid_report_id_returns_404(self, client):
        for bad in ("../etc/passwd", "abc", "600519_bogus"):
            resp = client.get(f"/reports/{bad}")
            assert resp.status_code == 404, f"should reject {bad}"

    def test_found_returns_detail(self, client, monkeypatch, tmp_path):
        md = tmp_path / "r.md"
        md.write_text("# 报告正文", encoding="utf-8")
        svc = MagicMock()
        svc.get_report.return_value = {
            "id": "600519_202606261200",
            "stock_code": "600519",
            "status": "success",
            "markdown": "# 报告正文",
        }
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_report",
            svc.get_report,
        )
        resp = client.get("/reports/600519_202606261200")
        assert resp.status_code == 200
        assert resp.json()["data"]["markdown"] == "# 报告正文"


# ============================================================
# delete_report
# ============================================================


class TestDeleteReport:
    def test_missing_returns_404(self, client, monkeypatch):
        svc = MagicMock()
        svc.delete_report.return_value = False
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.delete_report",
            svc.delete_report,
        )
        resp = client.delete("/reports/600519_202606261200")
        assert resp.status_code == 404

    def test_invalid_id_returns_404(self, client):
        for bad in ("badid", "../etc/passwd", "600519_bogus"):
            assert client.delete(f"/reports/{bad}").status_code == 404

    def test_success(self, client, monkeypatch):
        svc = MagicMock()
        svc.delete_report.return_value = True
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.delete_report",
            svc.delete_report,
        )
        resp = client.delete("/reports/600519_202606261200")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ============================================================
# download_pdf
# ============================================================


class TestDownloadPdf:
    def test_missing_record_returns_404(self, client, monkeypatch):
        svc = MagicMock()
        svc.get_report.return_value = None
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_report",
            svc.get_report,
        )
        resp = client.get("/reports/600519_202606261200/pdf")
        assert resp.status_code == 404

    def test_invalid_id_returns_404(self, client):
        resp = client.get("/reports/badid/pdf")
        assert resp.status_code == 404

    def test_pdf_generation_failure_returns_404(self, client, monkeypatch):
        svc = MagicMock()
        svc.get_report.return_value = {"id": "x"}
        svc.get_pdf_path.return_value = None
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_report",
            svc.get_report,
        )
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_pdf_path",
            svc.get_pdf_path,
        )
        resp = client.get("/reports/600519_202606261200/pdf")
        assert resp.status_code == 404

    def test_safe_path_returns_file(self, client, monkeypatch, tmp_path):
        pdf = tmp_path / "r.pdf"
        pdf.write_text("PDF", encoding="utf-8")
        svc = MagicMock()
        svc.get_report.return_value = {"id": "x"}
        svc.get_pdf_path.return_value = str(pdf)
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_report",
            svc.get_report,
        )
        monkeypatch.setattr(
            "src.services.policy_minesweeper_service.policy_minesweeper_service.get_pdf_path",
            svc.get_pdf_path,
        )
        monkeypatch.setattr(
            "api.v1.endpoints.policy_minesweeper.get_policy_minesweeper_dir",
            lambda: tmp_path,
        )
        resp = client.get("/reports/600519_202606261200/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
