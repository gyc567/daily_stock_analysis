# -*- coding: utf-8 -*-
"""三端点 PDF no-store 响应头测试（按 docs/pdf-generation-unification-plan.md §6.5）。

三个 PDF 下载端点（deep_research / policy_minesweeper / supply_chain）必须
设置：
- ``Cache-Control: no-store, no-cache, must-revalidate``
- ``Pragma: no-cache``
- ``Expires: 0``

禁止浏览器/中间层缓存旧 PDF。服务端 pdf_path 缓存仍复用，no-store 只要求
浏览器回源，不会每次重新渲染。

测试方式：裸 FastAPI 挂对应 router，mock service 层 get_report / get_pdf_path，
用临时目录创建 fake PDF，不跑真实 WeasyPrint。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ----------------------------------------------------------------------
# deep_research
# ----------------------------------------------------------------------


@pytest.fixture
def deep_research_app_client(monkeypatch, tmp_path):
    """裸 FastAPI 挂 deep_research router，service 全部 mock。"""
    from api.v1.endpoints import deep_research

    app = FastAPI()
    app.include_router(deep_research.router)

    pdf = tmp_path / "600519_202607011200.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    svc = MagicMock()
    svc.get_report.return_value = {"id": "600519_202607011200"}
    svc.get_pdf_path.return_value = str(pdf)
    monkeypatch.setattr("api.v1.endpoints.deep_research.deep_research_service", svc)
    # 路径收敛到 tmp_path（_resolve_safe_path 用 get_deep_research_dir()）
    monkeypatch.setattr(
        "api.v1.endpoints.deep_research.get_deep_research_dir",
        lambda: tmp_path,
    )

    return TestClient(app), pdf


def test_deep_research_pdf_has_no_store(deep_research_app_client):
    client, pdf = deep_research_app_client
    resp = client.get("/reports/600519_202607011200/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # 核心断言：no-store
    assert "no-store" in resp.headers.get("cache-control", "")
    assert "no-cache" in resp.headers.get("cache-control", "")
    assert "must-revalidate" in resp.headers.get("cache-control", "")
    assert resp.headers.get("pragma") == "no-cache"
    assert resp.headers.get("expires") == "0"


# ----------------------------------------------------------------------
# policy_minesweeper
# ----------------------------------------------------------------------


@pytest.fixture
def policy_minesweeper_app_client(monkeypatch, tmp_path):
    from api.v1.endpoints import policy_minesweeper

    app = FastAPI()
    app.include_router(policy_minesweeper.router)

    pdf = tmp_path / "600519_202607011200.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    svc = MagicMock()
    svc.get_report.return_value = {"id": "600519_202607011200"}
    svc.get_pdf_path.return_value = str(pdf)
    monkeypatch.setattr(
        "api.v1.endpoints.policy_minesweeper.policy_minesweeper_service", svc
    )
    monkeypatch.setattr(
        "api.v1.endpoints.policy_minesweeper.get_policy_minesweeper_dir",
        lambda: tmp_path,
    )

    return TestClient(app), pdf


def test_policy_minesweeper_pdf_has_no_store(policy_minesweeper_app_client):
    client, pdf = policy_minesweeper_app_client
    resp = client.get("/reports/600519_202607011200/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "no-store" in resp.headers.get("cache-control", "")
    assert "no-cache" in resp.headers.get("cache-control", "")
    assert "must-revalidate" in resp.headers.get("cache-control", "")
    assert resp.headers.get("pragma") == "no-cache"
    assert resp.headers.get("expires") == "0"


# ----------------------------------------------------------------------
# supply_chain
# ----------------------------------------------------------------------


@pytest.fixture
def supply_chain_app_client(monkeypatch, tmp_path):
    from api.v1.endpoints import supply_chain_reports

    app = FastAPI()
    app.include_router(supply_chain_reports.router)

    pdf = tmp_path / "sc_202607011500_1.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    svc = MagicMock()
    svc.get_report.return_value = {"id": "sc_202607011500_1"}
    svc.get_pdf_path.return_value = str(pdf)
    monkeypatch.setattr(
        "api.v1.endpoints.supply_chain_reports.supply_chain_report_service", svc
    )
    monkeypatch.setattr(
        "api.v1.endpoints.supply_chain_reports.get_supply_chain_report_dir",
        lambda: tmp_path,
    )

    return TestClient(app), pdf


def test_supply_chain_pdf_has_no_store(supply_chain_app_client):
    client, pdf = supply_chain_app_client
    resp = client.get("/reports/sc_202607011500_1/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "no-store" in resp.headers.get("cache-control", "")
    assert "no-cache" in resp.headers.get("cache-control", "")
    assert "must-revalidate" in resp.headers.get("cache-control", "")
    assert resp.headers.get("pragma") == "no-cache"
    assert resp.headers.get("expires") == "0"


# ----------------------------------------------------------------------
# 共同回归：no-store 与 Content-Disposition 共存
# ----------------------------------------------------------------------


def test_no_store_coexists_with_content_disposition(deep_research_app_client):
    """no-store headers 与业务文件名（``filename*=UTF-8''...``）共存。"""
    client, _pdf = deep_research_app_client
    resp = client.get("/reports/600519_202607011200/pdf")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    # 业务文件名按 docs/pdf-download-filename-plan.md（fallback 到 code）：
    # ``600519（600519）深度投研报告20260701.pdf`` —— 编码后含 ``深度投研报告``
    # 的 percent-encoded UTF-8 字节。
    assert "filename*=utf-8''" in cd
    # URL decode 后的业务名应包含报告类型 + 日期 + 代码
    import re as _re

    m = _re.search(r"filename\*=utf-8''([^;]+)", cd, _re.IGNORECASE)
    assert m is not None
    from urllib.parse import unquote

    decoded = unquote(m.group(1))
    assert "深度投研报告" in decoded
    assert "20260701" in decoded
    # 不再使用旧的 ASCII 名
    assert "deep_research_600519_202607011200.pdf" not in cd
    # 双重确认 no-store
    assert "no-store" in resp.headers.get("cache-control", "")
