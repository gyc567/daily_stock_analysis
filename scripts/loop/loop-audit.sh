#!/usr/bin/env bash
# loop-audit.sh — Loop Ready 审计工具
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TOTAL_SCORE=0
MAX_SCORE=110

check_file() {
    local file="$1" desc="$2" weight="$3"
    if [[ -f "$ROOT_DIR/$file" ]]; then
        echo -e "${GREEN}✓${NC} $file ($desc)"
        TOTAL_SCORE=$((TOTAL_SCORE + weight))
    else
        echo -e "${RED}✗${NC} $file ($desc)"
    fi
}

check_dir() {
    local dir="$1" desc="$2" weight="$3"
    if [[ -d "$ROOT_DIR/$dir" ]]; then
        echo -e "${GREEN}✓${NC} $dir/ ($desc)"
        TOTAL_SCORE=$((TOTAL_SCORE + weight))
    else
        echo -e "${RED}✗${NC} $dir/ ($desc)"
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Loop Ready Audit${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Repository: $ROOT_DIR"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo -e "${BLUE}1. 核心文件 (24 分)${NC}"
check_file "LOOP.md" "Loop 运营总览" 4
check_file "STATE.md" "Loop 状态文件" 4
check_file "LOOP_BUDGET.md" "Token 预算" 4
check_file "LOOP_CONSTRAINTS.md" "约束规则" 4
check_file "gate.yaml" "安全门禁" 4
check_file "loop-run-log.md" "运行日志" 4
echo ""

echo -e "${BLUE}2. Skills (20 分)${NC}"
check_dir ".claude/skills/loop-triage" "Loop Triage Skill" 5
check_dir ".claude/skills/loop-verify" "Loop Verify Skill" 5
check_dir ".claude/skills/loop-context" "Loop Context Skill" 5
check_dir ".claude/skills/loop-plan" "Loop Plan Skill" 5
echo ""

echo -e "${BLUE}3. Workflows (14 分)${NC}"
check_file ".github/workflows/loop-triage.yml" "Daily Triage" 5
check_file ".github/workflows/loop-ci-sweeper.yml" "CI Sweeper" 5
check_file ".github/workflows/loop-dep-sweeper.yml" "Dep Sweeper" 4
echo ""

echo -e "${BLUE}4. 安全机制 (12 分)${NC}"
check_file "scripts/loop/loop-gate.sh" "Gate 检查脚本" 4
check_file "scripts/loop/loop-audit.sh" "审计脚本" 4
check_file "scripts/loop/loop-budget.sh" "预算脚本" 4
echo ""

echo -e "${BLUE}5. 文档 (10 分)${NC}"
check_file "docs/loop-engineering-integration.md" "集成方案" 4
check_file "docs/loop-design-guide.md" "设计指南" 3
check_file "docs/loop-operating.md" "运营手册" 2
check_file "docs/loop-failure-modes.md" "失败模式" 1
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  审计结果${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Loop Ready Score: ${GREEN}$TOTAL_SCORE/${MAX_SCORE}${NC}"
echo ""

if [[ $TOTAL_SCORE -ge 80 ]]; then
    echo -e "Status: ${GREEN}Loop Ready (L2)${NC}"
    echo -e "建议: 可以运行 L2 级别的 Loop"
elif [[ $TOTAL_SCORE -ge 60 ]]; then
    echo -e "Status: ${GREEN}Loop Ready (L1)${NC}"
    echo -e "建议: 核心文件和 Workflow 已完成，可以运行 L1 Loop"
elif [[ $TOTAL_SCORE -ge 40 ]]; then
    echo -e "Status: ${YELLOW}Partially Ready${NC}"
    echo -e "建议: 优先完成 Workflow"
else
    echo -e "Status: ${RED}Not Ready${NC}"
    echo -e "建议: 需要继续完善"
fi
echo ""
echo "完成度: $(( (TOTAL_SCORE * 100) / MAX_SCORE ))%"
echo "目标分数: $MAX_SCORE"
