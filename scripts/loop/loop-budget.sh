#!/usr/bin/env bash
# =============================================================================
# loop-budget.sh — Loop 预算检查工具
# 检查 Token 消耗是否在预算范围内
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUDGET_FILE="$ROOT_DIR/LOOP_BUDGET.md"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 默认预算
DEFAULT_DAILY_TOKENS=50000
DEFAULT_WEEKLY_TOKENS=500000
DEFAULT_MONTHLY_TOKENS=2000000
WARNING_THRESHOLD=0.8

show_help() {
    cat << EOF
loop-budget.sh — Loop 预算检查工具

用法:
    $0 status              # 显示当前预算状态
    $0 check --loop <name> --tokens <input>/<output>
    $0 estimate --loop <name>
    $0 record --loop <name> --tokens <input>/<output>

示例:
    $0 status
    $0 check --loop daily-triage --tokens 30000/5000
    $0 estimate --loop daily-triage
    $0 record --loop daily-triage --tokens 30000/5000

Loops:
    daily-triage     - Daily Triage (L1)
    ci-sweeper       - CI Sweeper (L2)
    dep-sweeper      - Dependency Sweeper (L2)
    changelog-drafter - Changelog Drafter (L1)
EOF
}

# 获取 Loop 预算
get_loop_budget() {
    local loop="$1"
    case "$loop" in
        daily-triage)
            echo "50k" ;;
        ci-sweeper)
            echo "100k" ;;
        dep-sweeper)
            echo "80k" ;;
        changelog-drafter)
            echo "30k" ;;
        *)
            echo "50k" ;;
    esac
}

# 估算 Token 消耗
estimate() {
    local loop="$1"
    local budget
    budget=$(get_loop_budget "$loop")
    echo "=== Token 估算 ==="
    echo "Loop: $loop"
    echo "日预算: $budget tokens"
    echo ""
    echo "模型成本估算 (GPT-4o):"
    echo "  Input: ~$(( ${budget%k} * 3 / 1000 )) cents"
    echo "  Output: ~$(( ${budget%k} * 10 / 1000 )) cents"
    echo ""
    echo "模型成本估算 (Gemini 1.5):"
    echo "  Input: ~$(( ${budget%k} / 10000 )) cents"
    echo "  Output: ~$(( ${budget%k} * 5 / 100000 )) cents"
}

# 检查预算
check() {
    local loop="$1"
    local tokens="$2"
    local budget
    budget=$(get_loop_budget "$loop")
    local budget_num=${budget%k}
    local budget_tokens=$((budget_num * 1000))
    
    # 解析 input/output
    local input_tokens=${tokens%/*}
    local output_tokens=${tokens#*/}
    local total_tokens=$((input_tokens + output_tokens))
    
    echo "=== 预算检查 ==="
    echo "Loop: $loop"
    echo "消耗: ${input_tokens}/${output_tokens} tokens"
    echo "总计: $total_tokens tokens"
    echo "预算: $budget_tokens tokens"
    echo ""
    
    local ratio
    ratio=$(echo "scale=2; $total_tokens / $budget_tokens" | bc 2>/dev/null || echo "0")
    
    if (( $(echo "$ratio > 1" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "${RED}✗ 超出预算: ${ratio}x${NC}"
        return 1
    elif (( $(echo "$ratio > $WARNING_THRESHOLD" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "${YELLOW}⚠ 警告: ${ratio}x (超过 80%)${NC}"
        return 0
    else
        echo -e "${GREEN}✓ 在预算范围内${NC}"
        return 0
    fi
}

# 记录消耗
record() {
    local loop="$1"
    local tokens="$2"
    local log_file="$ROOT_DIR/loop-run-log.md"
    
    echo "=== 记录消耗 ==="
    echo "Loop: $loop"
    echo "Tokens: $tokens"
    echo ""
    
    # 追加到运行日志
    {
        echo ""
        echo "### $(date '+%Y-%m-%d %H:%M:%S')"
        echo "| 字段 | 值 |"
        echo "| --- | --- |"
        echo "| Loop | $loop |"
        echo "| Tokens | $tokens |"
        echo "| Result | success |"
    } >> "$log_file"
    
    echo -e "${GREEN}✓ 已记录到 loop-run-log.md${NC}"
}

# 显示状态
status() {
    echo "=== Loop 预算状态 ==="
    echo ""
    echo "| Loop | 日预算 | 当前消耗 | 状态 |"
    echo "| --- | --- | --- | --- |"
    echo "| daily-triage | 50k | - | ⚪ |"
    echo "| ci-sweeper | 100k | - | ⚪ |"
    echo "| dep-sweeper | 80k | - | ⚪ |"
    echo "| changelog-drafter | 30k | - | ⚪ |"
    echo ""
    echo "详细状态请查看: $BUDGET_FILE"
}

# 主入口
main() {
    case "${1:-}" in
        status)
            shift
            status "$@"
            ;;
        check)
            shift
            local loop=""
            local tokens=""
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --loop) loop="$2"; shift 2 ;;
                    --tokens) tokens="$2"; shift 2 ;;
                    *) shift ;;
                esac
            done
            [[ -z "$loop" ]] || [[ -z "$tokens" ]] && echo "Usage: $0 check --loop <name> --tokens <input>/<output>" && exit 1
            check "$loop" "$tokens"
            ;;
        estimate)
            shift
            local loop="${1:-daily-triage}"
            estimate "$loop"
            ;;
        record)
            shift
            local loop=""
            local tokens=""
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --loop) loop="$2"; shift 2 ;;
                    --tokens) tokens="$2"; shift 2 ;;
                    *) shift ;;
                esac
            done
            [[ -z "$loop" ]] || [[ -z "$tokens" ]] && echo "Usage: $0 record --loop <name> --tokens <input>/<output>" && exit 1
            record "$loop" "$tokens"
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"
