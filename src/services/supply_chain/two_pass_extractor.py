# -*- coding: utf-8 -*-
"""
[Supply Chain v2] 两轮供应链抽取器。

V1 失败原因：KB 文档里『宁德依赖 XX 公司前五大供应商之一』，
LLM 一次抽取只产出『XX 公司』，丢失了『前五大』这个关键关系强度信息。

V2 解决：
1. 第一轮（实体识别）：KB + LLM 产出 List[str] 候选实体
2. 第二轮（属性补全）：对每个实体反向检索 KB 全文 + 公开数据补字段

输入：第一轮输出 + KB 检索结果 + 公开数据
输出：List[ChainNodeV3]（结构化节点）
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.schemas.supply_chain import ChainNodeV3, FieldSource
from src.services.supply_chain.field_enrichment import SupplyChainFieldEnricher
from src.services.supply_chain.kb_retriever import (
    SupplyChainKBResult,
    SupplyChainKBRetriever,
)

logger = logging.getLogger(__name__)


# 行业默认子层（V1 _infer_from_industry 的轻量版，仅用于 sub_layer 默认填充）
INDUSTRY_SUB_LAYER_DEFAULTS: Dict[str, Dict[str, List[str]]] = {
    "半导体": {
        "upstream": ["硅片", "光刻胶", "EDA", "设备"],
        "downstream": ["消费电子", "汽车电子"],
    },
    "白酒": {"upstream": ["高粱", "小麦", "包装"], "downstream": ["高端消费", "商务"]},
    "新能源": {
        "upstream": ["锂矿", "隔膜", "电解液"],
        "downstream": ["新能源车", "储能"],
    },
    "医药": {"upstream": ["原料药", "辅料"], "downstream": ["医院", "药店"]},
    "光伏": {"upstream": ["硅料", "银浆", "玻璃"], "downstream": ["电站", "分布式"]},
}


class TwoPassSupplyChainExtractor:
    """两轮抽取流水线。

    用法：
        extractor = TwoPassSupplyChainExtractor(kb_retriever=kb, enricher=enricher)
        upstream_nodes, downstream_nodes = extractor.extract(
            ticker="600519",
            company="贵州茅台",
            kb_result=kb_result,
            llm_first_pass={"upstream": ["糯高粱", "小麦"], "downstream": ["高端消费者"]},
            industry_hint="高端白酒",
        )
    """

    def __init__(
        self,
        kb_retriever: Optional[SupplyChainKBRetriever] = None,
        enricher: Optional[SupplyChainFieldEnricher] = None,
    ) -> None:
        self._kb = kb_retriever or SupplyChainKBRetriever()
        self._enricher = enricher or SupplyChainFieldEnricher(kb_retriever=self._kb)

    def extract(
        self,
        ticker: str,
        company: str,
        kb_result: SupplyChainKBResult,
        llm_first_pass: Dict[str, Any],
        industry_hint: str = "",
    ) -> Tuple[List[ChainNodeV3], List[ChainNodeV3]]:
        """主入口。返回 (upstream_nodes, downstream_nodes)。

        步骤：
        1. 合并 KB + LLM 第一轮的实体集合（KB 优先，去重）
        2. 对每个实体做属性补全（公开数据 + KB 二次）
        3. 标记每个字段来源
        """
        upstream_names = self._merge_entities(
            kb_hits=kb_result.hits,
            llm_names=llm_first_pass.get("upstream", []) or [],
            layer="upstream",
            industry_hint=industry_hint,
        )
        downstream_names = self._merge_entities(
            kb_hits=kb_result.hits,
            llm_names=llm_first_pass.get("downstream", []) or [],
            layer="downstream",
            industry_hint=industry_hint,
        )

        upstream_nodes = [
            self._make_node(
                name=name,
                layer="upstream",
                kb_hits=kb_result.hits,
                ticker=ticker,
                industry_hint=industry_hint,
            )
            for name in upstream_names
        ]
        downstream_nodes = [
            self._make_node(
                name=name,
                layer="downstream",
                kb_hits=kb_result.hits,
                ticker=ticker,
                industry_hint=industry_hint,
            )
            for name in downstream_names
        ]

        # 第二轮：补全字段（公开数据 + KB）
        upstream_nodes = self._enricher.enrich_all(upstream_nodes)
        downstream_nodes = self._enricher.enrich_all(downstream_nodes)

        return upstream_nodes, downstream_nodes

    # ---------- 内部 ----------

    def _merge_entities(
        self,
        kb_hits: List[Any],
        llm_names: List[str],
        layer: str,
        industry_hint: str,
    ) -> List[str]:
        """合并 KB 命中片段里的实体 + LLM 抽取的实体（去重）。

        KB 实体抽取启发式：
        - 从 chunk content 里抓『上游』『下游』前后 30 字内的名词短语
        - 简化：用标点 / 顿号 / 空格切分 chunk content
        """
        kb_names: List[str] = []
        for hit in kb_hits:
            kb_names.extend(self._extract_names_from_hit(hit.content, layer))

        # 合并去重（保留顺序：KB 优先 + LLM 补充）
        seen = set()
        merged: List[str] = []
        for name in kb_names + [n.strip() for n in llm_names if n and n.strip()]:
            name = name.strip()
            if not name or name in seen or name in ("待分析", "未知", "null", "None"):
                continue
            seen.add(name)
            merged.append(name)

        return merged

    _NAME_PATTERNS = [
        re.compile(r"[，、；\n\r]"),
    ]

    def _extract_names_from_hit(self, content: str, layer: str) -> List[str]:
        """从 KB chunk 文本里抽取 layer 相关的实体名。

        启发式 V2：
        1. 找『上游』『下游』关键词所在句
        2. 取 marker 之后到句末的所有片段
        3. 用顿号/逗号/「和」「与」「及」细分
        4. 过滤掉『主要』『包括』『等』『为』『是』等修饰词
        """
        if not content:
            return []

        STOP_WORDS = {
            "主要",
            "包括",
            "等",
            "为",
            "是",
            "的",
            "与",
            "和",
            "及",
            "或",
            "上游",
            "下游",
            "产业链",
            "供应商",
            "客户",
            "厂商",
            "企业",
            "消费者",
            "领域",
            "应用",
            "生产",
            "销售",
            "服务",
        }

        # 后缀剥离（避免『小麦供应商』粘连）
        SUFFIX_TRIM = re.compile(
            r"(供应商|客户|厂商|企业|制造商|生产商|服务商|经销商|分销商|材料)$"
        )

        out: List[str] = []
        marker = "上游" if layer == "upstream" else "下游"
        for sentence in re.split(r"[。！？\n]", content):
            if marker not in sentence:
                continue
            idx = sentence.find(marker)
            tail = sentence[idx + len(marker) :]
            tail = re.sub(r"[和与及或]", "，", tail)
            if layer == "upstream":
                tail = re.split(r"下游|；|\n", tail)[0]
            else:
                tail = re.split(r"上游|；|\n", tail)[0]
            for piece in re.split(r"[、，：是为]", tail):
                piece = piece.strip()
                # 剥离尾部停用后缀
                piece = SUFFIX_TRIM.sub("", piece).strip()
                if (
                    2 <= len(piece) <= 20
                    and piece not in STOP_WORDS
                    and not re.search(r"\d+[%个家条]", piece)
                    and not re.search(r"^[的了在是我]", piece)
                ):
                    out.append(piece)
        return out

    def _make_node(
        self,
        name: str,
        layer: str,
        kb_hits: List[Any],
        ticker: str,
        industry_hint: str,
    ) -> ChainNodeV3:
        """构造 ChainNodeV3，根据 KB 命中标记 name_source。"""
        # 判断 name 来源
        name_source: FieldSource = "llm"
        name_doc_id: Optional[str] = None
        kb_age_days: Optional[int] = None

        for hit in kb_hits:
            if name and (name in hit.content or name in hit.document_title):
                name_source = "kb"
                name_doc_id = hit.document_id
                kb_age_days = hit.kb_doc_age_days
                break

        # 兜底：sub_layer 用行业默认
        sub_layer = self._guess_sub_layer(name, layer, industry_hint)

        return ChainNodeV3(
            name=name,
            layer=layer,
            sub_layer=sub_layer,
            relationship="一般",
            substitutability="未知",
            geographic_distribution=[],
            name_source=name_source,
            name_source_doc_id=name_doc_id,
            evidence_strength="kb_doc" if name_source == "kb" else "analysis",
            confidence="high" if name_source == "kb" else "medium",
            kb_doc_id=name_doc_id,
            kb_doc_age_days=kb_age_days,
        )

    def _guess_sub_layer(
        self, name: str, layer: str, industry_hint: str
    ) -> Optional[str]:
        """根据行业默认推测 sub_layer（轻量启发式，不强求）。"""
        if not industry_hint:
            return None
        for industry, defaults in INDUSTRY_SUB_LAYER_DEFAULTS.items():
            if industry in industry_hint:
                for sub in defaults.get(layer, []):
                    if sub in name:
                        return sub
        return None
