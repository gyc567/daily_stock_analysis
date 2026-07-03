# -*- coding: utf-8 -*-
"""
类型收窄工具函数（mypy 友好）。

提供一组 ``require_*`` 函数，用于在已校验的边界把 ``Optional[T]`` /
``T | None`` 收窄为 ``T``，避免下游代码到处写 ``assert x is not None`` 或
``if x is None: raise`` 的样板代码。

约定：
- 失败时抛 ``ValueError``（带 ``name`` 用于定位），不要抛 ``AssertionError``，
  因为 ``-O`` 模式下 ``assert`` 会被剥离，而收窄是类型契约的一部分。
- 函数名和签名稳定，调用方可以放心用。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, TypeVar

T = TypeVar("T")


def require_str(value: Optional[str], name: str) -> str:
    """要求 ``value`` 非 ``None``，否则抛 ``ValueError``。"""
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def require_int(value: Optional[int], name: str) -> int:
    """要求 ``value`` 非 ``None``，否则抛 ``ValueError``。"""
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def require_float(value: Optional[float], name: str) -> float:
    """要求 ``value`` 非 ``None``，否则抛 ``ValueError``。"""
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def require_bool(value: Optional[bool], name: str) -> bool:
    """要求 ``value`` 非 ``None``，否则抛 ``ValueError``。"""
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def require_dict(value: Optional[dict[str, Any]], name: str) -> dict[str, Any]:
    """要求 ``value`` 非 ``None`` 且为 ``dict``，否则抛 ``ValueError``。"""
    if value is None or not isinstance(value, dict):
        raise ValueError(f"{name} is required and must be a dict")
    return value


def require_list(value: Optional[list[Any]], name: str) -> list[Any]:
    """要求 ``value`` 非 ``None`` 且为 ``list``，否则抛 ``ValueError``。"""
    if value is None or not isinstance(value, list):
        raise ValueError(f"{name} is required and must be a list")
    return value


def require_datetime(value: Optional[datetime], name: str) -> datetime:
    """要求 ``value`` 非 ``None``，否则抛 ``ValueError``。"""
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def require_date(value: Optional[date], name: str) -> date:
    """要求 ``value`` 非 ``None``，否则抛 ``ValueError``。"""
    if value is None:
        raise ValueError(f"{name} is required")
    return value


def optional_str(value: Any, default: str = "") -> str:
    """把 ``Any | None`` 安全地转成 ``str``，``None`` 走 ``default``。"""
    if value is None:
        return default
    return str(value)


__all__ = [
    "require_str",
    "require_int",
    "require_float",
    "require_bool",
    "require_dict",
    "require_list",
    "require_datetime",
    "require_date",
    "optional_str",
]
