# -*- coding: utf-8 -*-
"""供应链分析 skill 数据目录定位。

数据落在 ``<repo>/data/supply_chain_skill/``（迁移自 serenity-skill，MIT），结构::

    SKILL.md                        核心方法论指令（236 行）
    references/                     8 个深度参考（按需注入 system prompt）
    assets/                         打分卡模板 / prompt 包 / 研报模板
    scripts/serenity_scorecard.py   瓶颈打分纯函数库（8 因子 + 8 惩罚）
    examples/                       输出样例（few-shot）
    evals/test-cases.md             6 个行为测试

路径可用环境变量 ``SUPPLY_CHAIN_DATA_DIR`` 覆盖。
"""

import os
from functools import lru_cache

# src/services/supply_chain/paths.py -> 上溯 4 级到仓库根
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_DEFAULT_DATA_DIR = os.path.join(_REPO_ROOT, "data", "supply_chain_skill")

# 注入 system prompt 的核心 references（审计修正：serenity-dialogue-protocol 是正确文件名）
CORE_REFERENCES = (
    "deep-research-workflow",
    "evidence-ladder",
    "market-source-playbook",
    "serenity-dialogue-protocol",
    "output-style-and-language",
)


@lru_cache(maxsize=1)
def data_dir() -> str:
    """供应链 skill 数据根目录。"""
    return os.environ.get("SUPPLY_CHAIN_DATA_DIR") or _DEFAULT_DATA_DIR


def skill_path() -> str:
    return os.path.join(data_dir(), "SKILL.md")


def references_dir() -> str:
    return os.path.join(data_dir(), "references")


def reference_path(name: str) -> str:
    return os.path.join(references_dir(), f"{name}.md")


def scorecard_script_path() -> str:
    return os.path.join(data_dir(), "scripts", "serenity_scorecard.py")
