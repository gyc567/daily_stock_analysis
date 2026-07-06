#!/usr/bin/env bash

set -euo pipefail

# 探测项目自带的 venv：优先 ./venv/bin/python，找不到 fallback 系统 python3。
# 复盘文档 §6: 直接调用系统 python 会导致 icontract/fastapi 等依赖缺失，
# 这里强制优先 venv，避免 CI 脚本环境假设与本地不一致。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [ -x "${REPO_ROOT}/venv/bin/python" ]; then
  PY="${REPO_ROOT}/venv/bin/python"
elif [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
  PY="${REPO_ROOT}/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python || true)"
  if [ -z "${PY}" ]; then
    echo "ERROR: 未找到 Python 解释器（需要 ./venv/bin/python 或系统 python3）" >&2
    exit 2
  fi
  echo "WARN: 未找到 ./venv/bin/python，回退到 ${PY}（若依赖缺失请先激活 venv）" >&2
fi

syntax_check() {
  echo "==> backend-gate: Python syntax check"
  "${PY}" -m py_compile main.py src/config.py src/auth.py src/analyzer.py src/notification.py
  "${PY}" -m py_compile src/storage.py src/scheduler.py src/search_service.py
  "${PY}" -m py_compile src/market_analyzer.py src/stock_analyzer.py
  "${PY}" -m py_compile data_provider/*.py
}

flake8_checks() {
  echo "==> backend-gate: flake8 critical checks"
  "${PY}" -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
}

deterministic_checks() {
  echo "==> backend-gate: local deterministic checks"
  ./scripts/test.sh code
  ./scripts/test.sh yfinance
}

offline_test_suite() {
  echo "==> backend-gate: offline test suite"
  "${PY}" -m pytest -m "not network"
}

run_all() {
  syntax_check
  flake8_checks
  deterministic_checks
  offline_test_suite
  echo "==> backend-gate: all checks passed"
}

phase="${1:-all}"

case "$phase" in
  all)
    run_all
    ;;
  syntax)
    syntax_check
    ;;
  flake8)
    flake8_checks
    ;;
  deterministic)
    deterministic_checks
    ;;
  offline-tests)
    offline_test_suite
    ;;
  *)
    echo "Usage: $0 [all|syntax|flake8|deterministic|offline-tests]" >&2
    exit 2
    ;;
esac
