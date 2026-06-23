# -*- coding: utf-8 -*-
"""serenity_scorecard 的加载与封装。

serenity_scorecard 是纯函数库（stdlib only），通过 importlib 从
``data/supply_chain_skill/scripts/serenity_scorecard.py`` 动态加载，
保持 upstream 脚本原样（便于版本对照/更新），无需 subprocess。
"""

from __future__ import annotations

import importlib.util
from typing import Any, Dict, Tuple

from src.services.supply_chain.paths import scorecard_script_path

_SCORECARD_MODULE = None


def _load_module():
    global _SCORECARD_MODULE
    if _SCORECARD_MODULE is None:
        path = scorecard_script_path()
        spec = importlib.util.spec_from_file_location("_serenity_scorecard", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 serenity_scorecard: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SCORECARD_MODULE = module
    return _SCORECARD_MODULE


def score(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """对一份瓶颈打分卡输入计算 ``(result_dict, verdict_str)``。"""
    return _load_module().score(data)


def to_markdown(result: Dict[str, Any]) -> str:
    """把 score() 返回的 result_dict 渲染成 Markdown 表格。

    上游英文版，保留给 upstream CLI / 对齐对照。工具层用 :func:`to_markdown_zh`。
    """
    return _load_module().to_markdown(result)


# ---- 中文渲染（工具层用，避免泄露内部 snake_case 字段名） ----
#
# system prompt 输出契约要求"不要输出内部记号（文件名/章节号/字段名）"，但上游
# ``to_markdown`` 直接用 factor/penalty 的 snake_case key 做表行，会被 LLM 原样
# 抄进最终答案。这里用中文人话标签重新渲染，与上游英文版并存。
_FACTOR_LABEL_ZH: Dict[str, str] = {
    "demand_inflection": "需求拐点",
    "architecture_coupling": "架构耦合",
    "chokepoint_severity": "卡点严重度",
    "supplier_concentration": "供应商集中度",
    "expansion_difficulty": "扩产难度",
    "evidence_quality": "证据质量",
    "valuation_disconnect": "估值脱节",
    "catalyst_timing": "催化时点",
}
_PENALTY_LABEL_ZH: Dict[str, str] = {
    "dilution_financing": "稀释/融资",
    "governance": "治理",
    "geopolitics": "地缘风险",
    "liquidity": "流动性",
    "hype_risk": "炒作风险",
    "accounting_quality": "会计质量",
    "cyclicality": "周期性",
    "alternative_design_risk": "替代路线",
}
_VERDICT_ZH: Dict[str, str] = {
    "Top research priority": "顶级研究优先级",
    "High research priority": "高研究优先级",
    "Worth tracking": "值得跟踪",
    "Early lead or low priority": "早期线索或低优先级",
}


def verdict_zh(verdict: str) -> str:
    """上游英文 verdict → 中文；未知值原样返回（不崩）。"""
    return _VERDICT_ZH.get(verdict, verdict)


def to_markdown_zh(result: Dict[str, Any]) -> str:
    """渲染中文瓶颈打分卡 Markdown（人话标签，不含内部字段名）。"""
    title_bits = [result.get("ticker") or "未知"]
    if result.get("company"):
        title_bits.append(f"（{result['company']}）")
    title = " ".join(title_bits)

    lines = [
        f"# 瓶颈打分卡：{title}",
        "",
        f"市场：{result.get('market', '')}",
        f"总分：**{result.get('final_score', 0)} / 100**",
        f"评级：**{verdict_zh(result.get('verdict', ''))}**",
        f"因子合计：{result.get('raw_factor_points', 0)}",
        f"惩罚合计：{result.get('penalty_points', 0)}",
        "",
        "## 因子",
        "| 因子 | 评分 | 权重 | 得分 |",
        "|---|---:|---:|---:|",
    ]
    for key, detail in result.get("factor_details", {}).items():
        label = _FACTOR_LABEL_ZH.get(key, key)
        lines.append(
            f"| {label} | {detail.get('rating', 0)} | "
            f"{detail.get('weight', 0)} | {detail.get('points', 0)} |"
        )

    lines.extend(["", "## 惩罚项", "| 惩罚项 | 评分 | 扣分 |", "|---|---:|---:|"])
    for key, detail in result.get("penalty_details", {}).items():
        label = _PENALTY_LABEL_ZH.get(key, key)
        lines.append(f"| {label} | {detail.get('rating', 0)} | {detail.get('points', 0)} |")

    weakening = [str(x).strip() for x in result.get("kill_switches", []) if str(x).strip()]
    if weakening:
        lines.extend(["", "## 可能削弱判断的因素"])
        for item in weakening:
            lines.append(f"- {item}")

    evidence_lines = []
    for ev in result.get("evidence", []):
        if isinstance(ev, dict):
            claim = str(ev.get("claim", "")).strip()
            source = str(ev.get("source", "")).strip()
            strength = str(ev.get("strength", "")).strip()
            if claim or source:
                evidence_lines.append(f"- [{strength}] {claim} — {source}")
    if evidence_lines:
        lines.extend(["", "## 证据备注"])
        lines.extend(evidence_lines)

    lines.append("")
    return "\n".join(lines)
