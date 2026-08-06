#!/usr/bin/env bash
# ponytail-check.sh - Ponytail 极简主义检查工具
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
show_help() { cat << 'EOF'
Ponytail Check - 极简主义代码检查
用法: ponytail-check.sh <命令>
命令: review | audit | help
EOF
}
print_header() { echo -e "${BLUE}=== Ponytail: $1 ===${NC}"; }
excl='src/|tests/|api/|scripts/|apps/|bot/|data_provider/'
check_utility() {
    echo -e "\n${YELLOW}工具函数检测:${NC}"
    local r=$(grep -r 'utils\.py\|helpers\.py\|common\.py' $excl --include='*.py' 2>/dev/null | grep -v '.pyc' | head -5)
    [[ -z "$r" ]] && echo -e "${GREEN}✓ 无问题${NC}" || echo "$r"
}
check_debug() {
    echo -e "\n${YELLOW}调试代码检测:${NC}"
    local p=$(grep -rn '^\s*print(' $excl --include='*.py' 2>/dev/null | wc -l)
    [[ "$p" -eq 0 ]] && echo -e "${GREEN}✓ 无 print${NC}" || echo -e "${YELLOW}⚠ print 语句: $p 处${NC}"
}
check_todos() {
    echo -e "\n${YELLOW}TODO/FIXME 检测:${NC}"
    local t=$(grep -rn 'TODO\|FIXME' $excl --include='*.py' 2>/dev/null | wc -l)
    [[ "$t" -eq 0 ]] && echo -e "${GREEN}✓ 无 TODO${NC}" || echo -e "${YELLOW}⚠ TODO/FIXME: $t 处${NC}"
}
check_markers() {
    echo -e "\n${YELLOW}ponytail 标记:${NC}"
    local m=$(grep -rn 'ponytail:' $excl --include='*.py' 2>/dev/null)
    [[ -z "$m" ]] && echo -e "${GREEN}✓ 无标记${NC}" || echo "$m"
}
show_stats() {
    echo -e "\n${YELLOW}统计:${NC}"
    echo "  文件: $(find src tests api scripts apps bot data_provider -name '*.py' 2>/dev/null | wc -l)"
    echo "  行数: $(find src tests api scripts apps bot data_provider -name '*.py' -exec cat {} \; 2>/dev/null | wc -l)"
}
cmd_review() { print_header 'Review'; check_utility; check_debug; check_todos; echo -e "\n${GREEN}✓ 完成${NC}"; }
cmd_audit() { print_header 'Audit'; check_utility; check_debug; check_todos; check_markers; show_stats; echo -e "\n${GREEN}✓ 完成${NC}"; }
main() { case "${1:-}" in review) cmd_review;; audit) cmd_audit;; help|'') show_help;; *) echo "Unknown: $1"; show_help; exit 1;; esac; }
[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
