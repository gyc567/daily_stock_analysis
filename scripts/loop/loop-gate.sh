#!/usr/bin/env bash
# =============================================================================
# loop-gate.sh — Loop Gate 检查工具
# 检查文件路径是否符合 gate.yaml 的安全规则
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE_FILE="$ROOT_DIR/gate.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_gate_file() {
    if [[ ! -f "$GATE_FILE" ]]; then
        echo -e "${RED}Error: gate.yaml not found${NC}" >&2
        exit 1
    fi
}

parse_yaml() {
    local section="$1"
    grep -A 50 "^${section}:" "$GATE_FILE" 2>/dev/null | \
        grep -E "^\s+-\s+" | sed 's/^\s*-\s*//' || true
}

match_pattern() {
    local path="$1"
    local pattern="$2"
    case "$pattern" in
        **)
            local prefix="${pattern%/\*\*/}"
            prefix="${prefix%/}"
            if [[ "$prefix" == "" ]]; then return 0; fi
            local suffix="${pattern#\*\*/}"
            [[ "$path" == *"$suffix"* ]] && return 0
            ;;
        *)
            local regex="${pattern//\*/[^/]*}"
            regex="${regex//\?/[^/]}"
            [[ "$path" =~ ^$regex$ ]] && return 0
            ;;
    esac
    return 1
}

check_denylist() {
    local paths="$1"
    local denylist
    denylist=$(parse_yaml "denylist")
    local IFS=$'\n'
    for path in $paths; do
        [[ -z "$path" ]] && continue
        for pattern in $denylist; do
            if match_pattern "$path" "$pattern"; then
                echo -e "${RED}✗ Denied: $path (pattern: $pattern)${NC}" >&2
                return 1
            fi
        done
    done
    return 0
}

check_require_review() {
    local paths="$1"
    local require_review
    require_review=$(parse_yaml "require-review")
    local violations=0
    local IFS=$'\n'
    for path in $paths; do
        [[ -z "$path" ]] && continue
        for pattern in $require_review; do
            if match_pattern "$path" "$pattern"; then
                echo -e "${YELLOW}⚠ Review: $path (pattern: $pattern)${NC}" >&2
                ((violations++))
            fi
        done
    done
    [[ $violations -gt 0 ]] && return 1
    return 0
}

check_max_files() {
    local paths="$1"
    local max_files
    max_files=$(grep "^max-files:" "$GATE_FILE" | awk '{print $2}')
    [[ -z "$max_files" ]] && max_files=10
    local count=0
    IFS=',' read -ra ARR <<< "$paths"
    for path in "${ARR[@]}"; do
        [[ -n "$path" ]] && ((count++))
    done
    if [[ $count -gt $max_files ]]; then
        echo -e "${RED}✗ Exceeded: $count files (max: $max_files)${NC}" >&2
        return 2
    fi
    return 0
}

check_auto_merge() {
    local paths="$1"
    local allowlist
    allowlist=$(parse_yaml "auto-merge-allowlist")
    local IFS=$'\n'
    for path in $paths; do
        [[ -z "$path" ]] && continue
        local allowed=0
        for pattern in $allowlist; do
            if match_pattern "$path" "$pattern"; then
                allowed=1 && break
            fi
        done
        [[ $allowed -eq 0 ]] && echo -e "${RED}✗ Not allowed: $path${NC}" >&2 && return 1
    done
    return 0
}

cmd_check() {
    local action=""
    local paths=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --action) action="$2"; shift 2 ;;
            --paths) paths="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -z "$action" ]] || [[ -z "$paths" ]] && echo "Usage: $0 check --action <action> --paths <paths>" && exit 1
    check_gate_file
    echo -e "${GREEN}=== Loop Gate Check ===${NC}"
    echo "Action: $action"
    echo "Paths: $paths"
    local result=0
    echo -e "${GREEN}[1/4] Checking denylist...${NC}"
    check_denylist "$paths" || result=1
    echo -e "${GREEN}[2/4] Checking max-files...${NC}"
    check_max_files "$paths" || result=2
    echo -e "${GREEN}[3/4] Action-specific check...${NC}"
    case "$action" in
        auto-merge) check_auto_merge "$paths" || result=1 ;;
        auto-edit|check) check_require_review "$paths" || result=1 ;;
    esac
    echo -e "${GREEN}[4/4] Done${NC}"
    [[ $result -eq 0 ]] && echo -e "${GREEN}✓ Passed${NC}" || echo -e "${RED}✗ Failed${NC}"
    exit $result
}

main() {
    case "${1:-}" in
        check) shift; cmd_check "$@" ;;
        *) echo "Usage: $0 check --action <action> --paths <paths>" ;;
    esac
}

main "$@"
