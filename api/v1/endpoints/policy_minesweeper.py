# -*- coding: utf-8 -*-
"""政策与公告双维度排雷 API endpoints。

形态：表单输入股票 → SSE 流式生成 → 报告展示 + PDF 下载 + 历史列表。
与问股/郑希/供应链的对话框模式不同（无多轮会话），但复用同一套 SSE 线程池包装。

接口（5 个，挂 ``/api/v1/policy-minesweeper``）：
- ``POST /generate/stream``  SSE 流式生成（thinking/tool_start/tool_done/generating/done/error/heartbeat）
- ``GET  /reports``          历史报告列表（分页）
- ``GET  /reports/{id}``     报告详情（含 Markdown 正文）
- ``DELETE /reports/{id}``   删除报告（元数据 + .md + .pdf）
- ``GET  /reports/{id}/pdf`` PDF 下载（惰性生成，``asyncio.to_thread``）

安全：
- ``report_id`` 白名单 ``^\\d{6}_\\d{12}$`` + ``_resolve_safe_path`` 双重防路径穿越。
- 入口 A 股代码格式由 Pydantic ``pattern=^\\d{6}$`` 在解析期校验（畸形直接 HTTP 422）；语义校验在 service.generate_report。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config import get_config
from src.services.policy_minesweeper_service import (
    PolicyMinesweeperInputError,
    get_policy_minesweeper_dir,
    policy_minesweeper_service,
)
from src.services.report_filename import format_stock_report_pdf_filename
from src.services.stock_code_utils import normalize_code

logger = logging.getLogger(__name__)

router = APIRouter()

STREAM_QUEUE_TIMEOUT_S = 960.0  # 略低于 nginx proxy_read_timeout(≥960s)
HEARTBEAT_INTERVAL_S = 30.0

# report_id 白名单：{6位A股代码}_{YYYYMMDDHHmm}，可选 _序号 后缀
_REPORT_ID_RE = re.compile(r"^\d{6}_\d{12}(_\d+)?$")


# ============================================================
# Schemas
# ============================================================


class PolicyMinesweeperRequest(BaseModel):
    # Layer 3（数据守门员）：I/O 边界第一道关 —— 格式/范围/枚举在解析期校验，
    # 畸形输入直接 422，不浪费 SSE 线程。语义级 A 股校验仍由 service 层 normalize_a_share 兜底。
    #
    # 注：``stock_code`` 接受多种输入格式（与前端 StockAutocomplete 的 canonicalCode 一致）：
    #   - 纯 6 位：``600519``
    #   - 后缀格式：``600519.SH`` / ``002617.SZ`` / ``920493.BJ``
    #   - 前缀格式：``SH600519`` / ``SZ000001`` / ``BJ920493``（不区分大小写）
    # ``field_validator`` 在解析期统一归一化为 6 位纯数字；非 A 股（HK / 美股）直接 422。
    # 这与 deep_research 的 ``endpoint 层 normalize_a_share 兜底`` 行为一致。
    model_config = ConfigDict(strict=True, frozen=True, validate_assignment=True)

    stock_code: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            max_length=20,
            description="A 股代码（6 位 / 含 .SH/.SZ/.BJ 后缀 / 含 SH/SZ 前缀，不区分大小写）",
        ),
    ]
    stock_name: Optional[Annotated[str, Field(min_length=1, max_length=64)]] = None
    horizon: Literal["short", "medium", "long"] = "medium"

    @field_validator("stock_code", mode="before")
    @classmethod
    def _normalize_stock_code(cls, v: Any) -> str:
        """归一化股票代码：``600519.SH`` / ``SH600519`` / 前后空格 → ``600519``。

        非 A 股（HK / 美股 / 无法识别）→ 直接 422，不浪费 SSE 线程。
        """
        if not isinstance(v, str) or not v.strip():
            raise ValueError("股票代码不能为空")
        normalized = normalize_code(v.strip())
        if not normalized or not (normalized.isdigit() and len(normalized) == 6):
            raise ValueError(
                f"政策与公告排雷当前仅支持 A 股（6 位数字代码），收到：{v!r}"
            )
        return normalized


class ReportListItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    stock_code: str
    stock_name: Optional[str] = None
    created_at: Optional[str] = None
    status: Optional[str] = None
    horizon: Optional[str] = None
    alpha_ok: Optional[bool] = None
    beta_ok: Optional[bool] = None
    omega_ok: Optional[bool] = None
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    confidence: Optional[int] = None
    has_pdf: bool = False


class ReportListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    data: List[ReportListItem]
    total: int


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    data: Dict[str, Any]


# ============================================================
# Helpers
# ============================================================


def _validate_report_id(report_id: str) -> str:
    """report_id 白名单校验（防路径穿越第一道关）。不通过抛 404。"""
    if not report_id or not _REPORT_ID_RE.fullmatch(report_id):
        raise HTTPException(status_code=404, detail="报告不存在")
    return report_id


def _resolve_safe_path(path_str: str) -> Optional[Path]:
    """将报告文件路径收敛到 policy_minesweeper 目录内（防穿越第二道关）。"""
    if not path_str:
        return None
    try:
        root = get_policy_minesweeper_dir().resolve()
        candidate = Path(path_str).resolve()
        if candidate.is_relative_to(root):
            return candidate
    except (OSError, ValueError):
        pass
    return None


def _require_agent(config) -> None:
    if not config.is_agent_available():
        raise HTTPException(status_code=400, detail="Agent mode is not enabled")


# ============================================================
# 生成（SSE 流式）
# ============================================================


@router.post("/generate/stream")
async def generate_stream(request: PolicyMinesweeperRequest) -> StreamingResponse:
    """SSE 流式生成排雷报告。

    入口先同步校验 A 股代码（非 A 股直接 400，不浪费 SSE 连接），
    通过后在线程池跑 ``policy_minesweeper_service.generate_report``，
    progress_callback 把事件塞入 asyncio.Queue，event_generator 消费并加 30s 心跳。
    """
    config = get_config()
    _require_agent(config)

    # A 股代码格式已由 Pydantic pattern=^\d{6}$ 在解析期校验（畸形 422，不浪费 SSE 连接）；
    # 语义校验在 service.generate_report 内，run_sync 捕获后发 error 事件。
    loop = asyncio.get_running_loop()
    queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()

    def progress_callback(event: Dict[str, Any]) -> None:
        try:
            asyncio.run_coroutine_threadsafe(queue.put(event), loop)
        except RuntimeError:
            pass  # loop 已关闭，忽略

    def run_sync() -> None:
        try:
            policy_minesweeper_service.generate_report(
                raw_code=request.stock_code,
                raw_name=request.stock_name,
                horizon=request.horizon,
                progress_callback=progress_callback,
            )
        except PolicyMinesweeperInputError as exc:
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "error", "message": str(exc)}), loop
            )
        except Exception as exc:
            logger.error("[PolicyMinesweeper] stream error: %s", exc, exc_info=True)
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "error", "message": f"生成失败：{exc}"}), loop
            )

    async def event_generator():
        import time

        fut = loop.run_in_executor(None, run_sync)
        last_event_time = time.time()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=HEARTBEAT_INTERVAL_S
                    )
                except asyncio.TimeoutError:
                    if time.time() - last_event_time >= HEARTBEAT_INTERVAL_S:
                        yield (
                            "data: "
                            + json.dumps({"type": "heartbeat"}, ensure_ascii=False)
                            + "\n\n"
                        )
                    continue
                last_event_time = time.time()
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                if event.get("type") in ("done", "error"):
                    break
        finally:
            try:
                await asyncio.wait_for(fut, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as exc:
                logger.debug(
                    "[PolicyMinesweeper] executor cleanup error (ignored): %s", exc
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 关缓冲，配合 proxy_read_timeout >= 960s
            "Connection": "keep-alive",
        },
    )


# ============================================================
# 历史报告 CRUD
# ============================================================


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    stock_code: Optional[str] = Query(None),
):
    """历史报告列表（分页，按时间倒序）。"""
    rows, total = policy_minesweeper_service.list_reports(
        limit=limit, offset=offset, stock_code=stock_code
    )
    items = [
        ReportListItem(
            id=r.get("id", ""),
            stock_code=r.get("stock_code", ""),
            stock_name=r.get("stock_name"),
            created_at=r.get("created_at"),
            status=r.get("status"),
            horizon=r.get("horizon"),
            alpha_ok=r.get("alpha_ok"),
            beta_ok=r.get("beta_ok"),
            omega_ok=r.get("omega_ok"),
            composite_score=r.get("composite_score"),
            verdict=r.get("verdict"),
            confidence=r.get("confidence"),
            has_pdf=bool(r.get("pdf_path")),
        )
        for r in rows
    ]
    return ReportListResponse(success=True, data=items, total=total)


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report(report_id: str):
    """报告详情（含 Markdown 正文）。"""
    _validate_report_id(report_id)
    data = policy_minesweeper_service.get_report(report_id)
    if data is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return ReportDetailResponse(success=True, data=data)


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """删除报告（元数据 + .md + .pdf 文件）。"""
    _validate_report_id(report_id)
    ok = policy_minesweeper_service.delete_report(report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="报告不存在")
    logger.info("[PolicyMinesweeper] 删除报告 %s（via API）", report_id)
    return {"success": True, "deleted": report_id}


# ============================================================
# PDF 下载（惰性生成）
# ============================================================


@router.get("/reports/{report_id}/pdf")
async def download_pdf(report_id: str):
    """PDF 下载：惰性生成（首次请求在线程池生成，后续直接发文件）。"""
    _validate_report_id(report_id)

    record = await asyncio.to_thread(policy_minesweeper_service.get_report, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    pdf_path_str = await asyncio.to_thread(
        policy_minesweeper_service.get_pdf_path, report_id
    )
    if not pdf_path_str:
        raise HTTPException(
            status_code=404,
            detail="PDF 生成失败（渲染依赖不可用或报告正文为空），请稍后重试",
        )

    safe_path = _resolve_safe_path(pdf_path_str)
    if safe_path is None or not safe_path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在")

    # 业务文件名（按 docs/pdf-download-filename-plan.md）：
    # 科瑞技术（002957）政策与公告排雷报告20260630.pdf
    download_filename = format_stock_report_pdf_filename(
        stock_name=record.get("stock_name"),
        stock_code=record.get("stock_code") or report_id.split("_", 1)[0],
        report_type="policy_minesweeper",
        created_at=record.get("created_at"),
    )

    return FileResponse(
        str(safe_path),
        media_type="application/pdf",
        filename=download_filename,
        headers={
            # 按 docs/pdf-generation-unification-plan.md §6.5：禁止浏览器/中间层缓存 PDF。
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
