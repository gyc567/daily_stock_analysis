#!/usr/bin/env python3
"""
Graphify post-commit rebuild wrapper.

Uses the pipx-installed graphify (Python 3.14) to re-run AST-only graph
rebuild after each `git commit`.  No LLM, no semantic extraction — fast and
deterministic.

Usage (called from .git/hooks/post-commit):
    python3 scripts/graphify_rebuild.py

Or run manually:
    python3 scripts/graphify_rebuild.py [--scope <path>]

Exit codes:
    0  success (or nothing to do)
    1  error
"""

import sys
import os
from pathlib import Path

# ------------------------------------------------------------------
# Interpreter resolution: prefer the pipx-installed graphify venv python.
# Fall back to the bare `python3` on the PATH (may not have graphify
# if graphify was installed via pipx — see the install command below).
# ------------------------------------------------------------------
_PIPX_GRAPHIFY = "/Users/eric/.local/pipx/venvs/graphifyy/bin/python"
_FALLBACK_PY = sys.executable  # the python that ran this script


def _rebuild(watch_path: Path, python: str) -> bool:
    """Call graphify.watch._rebuild_code via the given python interpreter."""
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from graphify.watch import _rebuild_code\n"
        "success = _rebuild_code(Path('.'))\n"
        "sys.exit(0 if success else 1)\n"
    )
    import subprocess

    result = subprocess.run(
        [python, "-c", code],
        cwd=str(watch_path.resolve()),
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def _has_graphify(python: str) -> bool:
    """Check whether the given python interpreter has graphify installed."""
    import subprocess

    result = subprocess.run(
        [python, "-c", "import graphify"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    """Rebuild the graph.  Returns 0 on success, 1 on error."""
    import argparse

    parser = argparse.ArgumentParser(description="Rebuild graphify graph after commit.")
    parser.add_argument(
        "--scope",
        type=Path,
        default=Path("src"),  # default: src/ only (~211 files, fast)
        help="Root path to scan for code files (default: src/)",
    )
    args = parser.parse_args()

    # Try pipx venv python first, then fall back to whatever python3 is on PATH.
    for python in (_PIPX_GRAPHIFY, _FALLBACK_PY):
        if _has_graphify(python):
            print(f"[graphify post-commit] using {python}")
            if _rebuild(args.scope, python):
                print("[graphify post-commit] graph rebuilt successfully.")
                return 0
            else:
                print("[graphify post-commit] rebuild returned False — no code files found.")
                return 0  # not an error: nothing to rebuild

    print(
        "[graphify post-commit] ERROR: graphify is not installed.\n"
        "  Install with: pip install graphifyy  (or: pipx install graphifyy)\n"
        "  Then re-run:  graphify hook install",
        file=sys.stderr,
    )
    return 1  # error — but do NOT block the commit (this runs post-commit)


if __name__ == "__main__":
    sys.exit(main())
