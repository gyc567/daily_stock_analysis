# -*- coding: utf-8 -*-
"""Shared pytest fixtures for tests/scoring/.

Issue: tests/scoring/test_p{1,2,3}_validation.py were written as standalone
test runners (using a local \`TestRunner\` class) and later wrapped with
\`def test_xxx(runner: TestRunner):\` parameter annotations, but no actual
\`runner\` fixture was provided. This conftest provides the missing fixture.

The \`TestRunner\` here is a unified helper that supports both
\`record(name, passed, message, details)\` (used by P1 and P2 tests) and
\`check(name, condition, message)\` (used by P3 tests), so the single
fixture works for all three files regardless of which local \`TestRunner\`
class they declare.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class TestRunner:
    """Unified test runner used by all scoring validation tests.

    Methods:
        record(name, passed, message, details) -> None  (P1/P2 style)
        check(name, condition, message) -> bool        (P3 style)
        summary() -> (passed_count, failed_count) or None
    """

    def __init__(self) -> None:
        self.passed: int = 0
        self.failed: int = 0
        self.results: List[Dict[str, Any]] = []
        self.errors: List[str] = []

    def record(
        self,
        name: str,
        passed: bool,
        message: str = "",
        details: str = "",
    ) -> None:
        self.results.append(
            {
                "name": name,
                "passed": passed,
                "message": message,
                "details": details,
            }
        )
        if passed:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            line = f"  ❌ {name}: {message}"
            self.errors.append(line)
            print(line)
        if details:
            print(f"     {details}")

    def check(self, name: str, condition: bool, message: str = "") -> bool:
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
            return True
        line = f"  [FAIL] {name}"
        if message:
            line += f" - {message}"
        self.errors.append(line)
        self.failed += 1
        print(line)
        return False

    def summary(self) -> Tuple[int, int] | None:
        # P1/P2 return (passed, failed); P3 prints and returns None.
        total = self.passed + self.failed
        print(f"\n{'=' * 60}")
        print(f"Validation Results: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for e in self.errors:
                print(e)
        print(f"{'=' * 60}")
        return None if total == 0 else (self.passed, self.failed)


import pytest


@pytest.fixture
def runner() -> TestRunner:
    """Provide a fresh TestRunner for each scoring validation test.

    Returned instance has both \`record()\` (P1/P2) and \`check()\` (P3)
    methods, so the same fixture works for all three test files.
    """
    return TestRunner()
