# -*- coding: utf-8 -*-
"""Tests for P2 PR-B5: strategies/midterm_compass.yaml loads as a skill."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.skills.base import SkillManager, load_skill_from_yaml


class TestStrategyYamlDefaultActiveFalse:
    def test_default_active_is_false(self) -> None:
        skill = load_skill_from_yaml(
            os.path.join(os.path.dirname(__file__), "..", "strategies", "midtrend_compass.yaml")
        )
        assert skill.default_active is False

    def test_name_and_category(self) -> None:
        skill = load_skill_from_yaml(
            os.path.join(os.path.dirname(__file__), "..", "strategies", "midtrend_compass.yaml")
        )
        assert skill.name == "midtrend_compass"
        assert skill.category == "trend"
        assert skill.instructions


class TestStrategyYamlLoadsViaSkillManager:
    def test_loads_via_skill_manager(self) -> None:
        manager = SkillManager()
        count = manager.load_builtin_strategies()
        assert count > 0
        loaded = [s for s in manager.list_skills() if s.name == "midtrend_compass"]
        assert len(loaded) == 1
        assert loaded[0].default_active is False

    def test_not_in_default_activation_set(self) -> None:
        # §13.4 frozen decision: default off — users opt in via strategy settings.
        manager = SkillManager()
        manager.load_builtin_strategies()
        defaults = [s for s in manager.list_skills() if s.default_active]
        assert all(s.name != "midtrend_compass" for s in defaults)


@pytest.mark.parametrize(
    "builtin",
    ["bull_trend", "chan_theory", "dragon_head"],
)
def test_other_builtin_strategies_still_load(builtin: str) -> None:
    manager = SkillManager()
    manager.load_builtin_strategies()
    names = {s.name for s in manager.list_skills()}
    assert builtin in names
