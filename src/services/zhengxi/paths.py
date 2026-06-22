# -*- coding: utf-8 -*-
"""郑希投研数据目录定位。

数据落在 ``<repo>/data/fund_manager_views/zhengxi/``，结构::

    corpus/              郑希公开观点语料（markdown，按类型分子目录）
    method.md            投资方法框架（从语料蒸馏，每条配原话佐证）
    scorecard.md         六维评分卡（满分 100）
    corpus_index.json    语料索引（类型/日期/标题/链接）
    fund_data/           8 只基金快照
        _index.json
        <code>_<name>/
            季度持仓.json
            净值业绩规模.json

路径可用环境变量 ``ZHENGXI_DATA_DIR`` 覆盖（用于测试或非标准部署）。
"""

import os
from functools import lru_cache

# src/services/zhengxi/paths.py -> 上溯 4 级到仓库根
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_DEFAULT_DATA_DIR = os.path.join(_REPO_ROOT, "data", "fund_manager_views", "zhengxi")


@lru_cache(maxsize=1)
def data_dir() -> str:
    """郑希数据根目录。"""
    return os.environ.get("ZHENGXI_DATA_DIR") or _DEFAULT_DATA_DIR


def corpus_dir() -> str:
    return os.path.join(data_dir(), "corpus")


def fund_data_dir() -> str:
    return os.path.join(data_dir(), "fund_data")


def method_path() -> str:
    return os.path.join(data_dir(), "method.md")


def scorecard_path() -> str:
    return os.path.join(data_dir(), "scorecard.md")


def corpus_index_path() -> str:
    return os.path.join(data_dir(), "corpus_index.json")
