# -*- coding: utf-8 -*-
"""``src.utils.type_guards`` 契约测试。"""

from __future__ import annotations

import pytest

from src.utils.type_guards import (
    optional_str,
    require_bool,
    require_date,
    require_datetime,
    require_dict,
    require_float,
    require_int,
    require_list,
    require_str,
)


def test_require_str_returns_value_when_present() -> None:
    assert require_str("hello", "field") == "hello"


def test_require_str_raises_when_none() -> None:
    with pytest.raises(ValueError, match="field is required"):
        require_str(None, "field")


def test_require_int_raises_when_none() -> None:
    with pytest.raises(ValueError, match="count is required"):
        require_int(None, "count")


def test_require_float_raises_when_none() -> None:
    with pytest.raises(ValueError):
        require_float(None, "ratio")


def test_require_bool_raises_when_none() -> None:
    with pytest.raises(ValueError):
        require_bool(None, "enabled")


def test_require_dict_raises_when_none() -> None:
    with pytest.raises(ValueError, match="must be a dict"):
        require_dict(None, "ctx")


def test_require_dict_raises_when_not_dict() -> None:
    with pytest.raises(ValueError, match="must be a dict"):
        require_dict("not a dict", "ctx")  # type: ignore[arg-type]


def test_require_list_raises_when_none() -> None:
    with pytest.raises(ValueError, match="must be a list"):
        require_list(None, "items")


def test_require_list_raises_when_not_list() -> None:
    with pytest.raises(ValueError, match="must be a list"):
        require_list({"k": 1}, "items")  # type: ignore[arg-type]


def test_require_datetime_raises_when_none() -> None:
    from datetime import datetime

    with pytest.raises(ValueError):
        require_datetime(None, "ts")
    assert isinstance(require_datetime(datetime.now(), "ts"), datetime)


def test_require_date_raises_when_none() -> None:
    from datetime import date

    with pytest.raises(ValueError):
        require_date(None, "d")
    assert require_date(date.today(), "d") == date.today()


def test_optional_str_handles_none() -> None:
    assert optional_str(None) == ""
    assert optional_str(None, default="x") == "x"
    assert optional_str(42) == "42"
    assert optional_str("hi") == "hi"
