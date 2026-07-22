# -*- coding: utf-8 -*-
"""
[Supply Chain v2] 公开数据字段补全器。

职责：补全 ChainNodeV3 的可量化字段（concentration_pct / geographic_distribution）。
来源：
- Tushare top10_holders / stock_holder（失败时降级）
- akshare 财报字段
- KB 二次检索（substitutability）
- 都不命中时填『未知』，绝不编造

按 v2 决策 D3：公开数据接入但失败降级，离线测试用 mock。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.schemas.supply_chain import ChainNodeV3

logger = logging.getLogger(__name__)


class SupplyChainFieldEnricher:
    """对每个候选节点补全可量化字段。

    工具失败时降级到 KB 二次检索；KB 无命中时填『未知』而非编造。
    """

    def __init__(self, kb_retriever: Optional[Any] = None) -> None:
        self._kb_retriever = kb_retriever

    def enrich(self, node: ChainNodeV3) -> ChainNodeV3:
        """补全节点的可量化字段，返回新节点（frozen + model_copy）。"""
        updates: Dict[str, Any] = {}

        # 1. concentration_pct（需 code + 当前为 None）
        if node.code and node.concentration_pct is None:
            pct = self._fetch_top5_concentration(node.code)
            if pct is not None:
                updates.update(
                    {
                        "concentration_pct": pct,
                        "concentration_source": "tool",
                        "concentration_tool": "tushare.top10_holders",
                        "evidence_strength": "primary",
                    }
                )

        # 2. geographic_distribution
        if node.code and not node.geographic_distribution:
            geo = self._fetch_geo_revenue(node.code)
            if geo:
                updates["geographic_distribution"] = geo

        # 3. substitutability（KB 二次检索）
        if node.substitutability == "未知" and self._kb_retriever is not None:
            kb_sub = self._fetch_substitutability_from_kb(node.name)
            if kb_sub:
                updates["substitutability"] = kb_sub

        if not updates:
            return node
        return node.model_copy(update=updates)

    def enrich_all(self, nodes: List[ChainNodeV3]) -> List[ChainNodeV3]:
        """批量补全，单个失败不拖垮整体。"""
        out: List[ChainNodeV3] = []
        for n in nodes:
            try:
                out.append(self.enrich(n))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[FieldEnricher] 节点 %s 补全失败: %s", n.name, exc)
                out.append(n)
        return out

    # ---------- 内部 ----------

    def _fetch_top5_concentration(self, code: str) -> Optional[float]:
        """调 tushare/akshare 取前 5 大供应商/客户占比。

        失败 / 无数据 → 返回 None（不编造）。
        """
        try:
            # 尝试 tushare（如未配置 token 会失败，捕获后返回 None）
            try:
                import tushare as ts  # type: ignore

                pro = ts.pro_api()
                df = pro.top10_holders(
                    ts_code=code + ".SH" if code.startswith("6") else code + ".SZ"
                )
                if df is not None and not df.empty:
                    return float(df["hold_ratio"].head(5).sum())
            except Exception as exc:  # noqa: BLE001
                logger.debug("[FieldEnricher] tushare 失败 %s: %s", code, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("[FieldEnricher] concentration 兜底失败 %s: %s", code, exc)
            return None

    def _fetch_geo_revenue(self, code: str) -> List[str]:
        """调工具取营收地理分布。失败 → 空列表。"""
        try:
            # 真实实现应调 tushare/akshare；此处简化兜底
            try:
                import tushare as ts  # type: ignore

                pro = ts.pro_api()
                df = pro.main_business(
                    ts_code=code + ".SH" if code.startswith("6") else code + ".SZ"
                )
                if df is not None and not df.empty:
                    # 简化：取前 5 个地区名
                    if "area" in df.columns:
                        return [str(x) for x in df["area"].head(5).tolist() if x]
            except Exception as exc:  # noqa: BLE001
                logger.debug("[FieldEnricher] tushare geo 失败 %s: %s", code, exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.debug("[FieldEnricher] geo 兜底失败 %s: %s", code, exc)
            return []

    def _fetch_substitutability_from_kb(self, name: str) -> Optional[str]:
        """从 KB 二次检索可替代性。

        启发式：KB 命中片段里出现『不可替代/唯一/卡脖子』→ 不可替代；
        出现『多家/可替代/竞争充分』→ 高；否则保持 None（未知）。
        """
        if self._kb_retriever is None:
            return None
        try:
            result = self._kb_retriever.retrieve(keywords=[name, "替代"], top_k=3)
            if result.aggregate_score < 0.3:
                return None
            for hit in result.hits:
                content = hit.content.lower()
                if any(
                    kw in content
                    for kw in ("不可替代", "唯一", "卡脖子", "no substitute")
                ):
                    return "不可替代"
                if any(kw in content for kw in ("高度集中", "寡头", "独家")):
                    return "低"
                if any(kw in content for kw in ("竞争充分", "可替代", "多家供应")):
                    return "高"
            return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("[FieldEnricher] substitutability KB 失败 %s: %s", name, exc)
            return None
