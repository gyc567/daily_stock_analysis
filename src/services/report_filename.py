# -*- coding: utf-8 -*-
"""PDF 下载文件名生成（按 docs/pdf-download-filename-plan.md）。

业务命名规则（与方案文档一致）：

- 单股报告（深度投研 / 政策与公告排雷）：

      股票中文名（股票代码）报告类型YYYYMMDD.pdf

  示例：``科瑞技术（002957）深度投研报告20260630.pdf``

  股票名为空时 fallback 到股票代码；命名日期取 ``created_at`` 的日期部分。

- 供应链分析（阶段 1 主题型）：

      主题供应链分析报告YYYYMMDD.pdf

  示例：``A股AI半导体供应链供应链分析报告20260630.pdf``

文件名清理规则：

- 移除 ``/ \\ : * ? " < > |``
- 移除换行与控制字符
- 压缩连续空白
- 保留中文、数字、字母与中文括号 ``（ ）``

后端 ``FileResponse`` 直接用 helper 构造 ``download_filename``；
前端 ``<a download>`` 不再硬编码（详见 ``apps/dsa-web/src/api/download.ts``）。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

# 报告类型 label（与方案文档 §后端方案 表格 一致）
STOCK_REPORT_TYPE_LABELS = {
    "deep_research": "深度投研报告",
    "policy_minesweeper": "政策与公告排雷报告",
    "supply_chain": "供应链分析报告",
}
TOPIC_REPORT_TYPE_LABEL = "供应链分析报告"

# 非法文件名字符：/ \ : * ? " < > |
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:\*\?"<>\|]')
# 换行 / 控制字符
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
# 中文括号与 ASCII 括号兼容：业务中只保留中文括号 "（ ）"；先一次性标准化
_ASCII_PARENS = re.compile(r"[\(\)]")
# 压缩连续空白
_MULTI_WHITESPACE = re.compile(r"\s+")


def _clean_filename_part(text: str) -> str:
    """清理文件名片段：移除非法字符、控制字符、ASCII 括号；压缩空白。"""
    if not text:
        return ""
    cleaned = _INVALID_FILENAME_CHARS.sub("", text)
    cleaned = _CONTROL_CHARS.sub("", cleaned)
    cleaned = _ASCII_PARENS.sub("", cleaned)
    cleaned = _MULTI_WHITESPACE.sub(" ", cleaned).strip()
    return cleaned


def _format_date(created_at: Optional[str]) -> str:
    """从 ISO 字符串 / datetime / None 取 ``YYYYMMDD``。无值时回退到今天。"""
    if isinstance(created_at, datetime):
        return created_at.strftime("%Y%m%d")
    if isinstance(created_at, str) and created_at.strip():
        s = created_at.strip()
        # 尝试 ISO 格式：2026-07-01T18:30:00 / 2026-07-01 18:30:00 / 2026-07-01
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(
                    s[: len(fmt) + 2 if "%f" not in fmt else 26], fmt
                ).strftime("%Y%m%d")
            except ValueError:
                continue
        # 兜底：取前 10 字符按 YYYY-MM-DD
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y%m%d")
        except ValueError:
            pass
    # 兜底到今天
    return datetime.now().strftime("%Y%m%d")


def format_stock_report_pdf_filename(
    stock_name: Optional[str],
    stock_code: Optional[str],
    report_type: str,
    created_at: Optional[str],
) -> str:
    """单股报告 PDF 文件名。

    Args:
        stock_name: 股票中文名（可能为 None 或空，fallback 到 stock_code）。
        stock_code: 6 位 A 股代码（fallback 源）。
        report_type: ``"deep_research"`` / ``"policy_minesweeper"``。
        created_at: 报告创建时间（ISO 字符串 / datetime）。

    Returns:
        例：``科瑞技术（002957）深度投研报告20260630.pdf``
    """
    label = STOCK_REPORT_TYPE_LABELS.get(report_type, "报告")
    name_part = _clean_filename_part(stock_name) if stock_name else ""
    code_part = _clean_filename_part(stock_code) if stock_code else ""
    display_name = name_part or code_part or "未知"
    date_part = _format_date(created_at)
    return f"{display_name}（{code_part}）{label}{date_part}.pdf"


def format_topic_report_pdf_filename(
    topic: str,
    created_at: Optional[str],
) -> str:
    """供应链分析报告 PDF 文件名（阶段 1 主题型，按方案文档 §供应链报告边界）。

    Args:
        topic: 报告主题（必填）。
        created_at: 报告创建时间（ISO 字符串 / datetime）。

    Returns:
        例：``A股AI半导体供应链供应链分析报告20260630.pdf``
    """
    topic_part = _clean_filename_part(topic) or "供应链分析"
    date_part = _format_date(created_at)
    return f"{topic_part}{TOPIC_REPORT_TYPE_LABEL}{date_part}.pdf"
