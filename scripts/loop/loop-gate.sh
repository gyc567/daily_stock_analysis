#!/usr/bin/env bash
# =============================================================================
# loop-gate.sh — Loop Gate 检查工具
# 检查文件路径是否符合 gate.yaml 的安全规则
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE_FILE="$ROOT_DIR/gate.yaml"
MATCH_SCRIPT="$SCRIPT_DIR/_match_pattern.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 创建 Python 匹配脚本（如果不存在）
if [[ ! -f "$MATCH_SCRIPT" ]]; then
    cat > "$MATCH_SCRIPT" << 'PYEOF'
import sys
import re

path = sys.argv[1]
pattern = sys.argv[2]

def match_glob(path, pattern):
    if '*' not in pattern and '?' not in pattern:
        return path == pattern
    
    i = 0
    regex_parts = []
    pattern_len = len(pattern)
    
    while i < pattern_len:
        c = pattern[i]
        
        if c == '*':
            if i + 1 < pattern_len and pattern[i+1] == '*':
                if i + 2 < pattern_len and pattern[i+2] == '/':
                    regex_parts.append('(?:.+/)?')
                    i += 3
                else:
                    regex_parts.append('.*')
                    i += 2
            else:
                regex_parts.append('[^/]*')
                i += 1
        elif c == '?':
            regex_parts.append('[^/]')
            i += 1
        elif c == '.':
            regex_parts.append('\\.')
            i += 1
        else:
            regex_parts.append(re.escape(c))
            i += 1
    
    regex = '^' + ''.join(regex_parts) + '$'
    return bool(re.match(regex, path))

sys.exit(0 if match_glob(path, pattern) else 1)
PYEOF
fi

check_gate_file() {
    if [[ ! -f "$GATE_FILE" ]]; then
        echo -e "${RED}Error: gate.yaml not found${NC}" >&2
        exit 1
    fi
}

# 使用 Python 解析 YAML section
parse_yaml() {
    local section="$1"
    python3 - "$section" "$GATE_FILE" << 'PYEOF'
import sys
import re

section = sys.argv[1]
gate_file = sys.argv[2]

with open(gate_file, 'r') as f:
    lines = f.readlines()

start_idx = None
for i, line in enumerate(lines):
    if re.match(rf'^\s*{re.escape(section)}:\s*$', line):
        start_idx = i
        break

if start_idx is None:
    sys.exit(0)

indent = None
for i in range(start_idx + 1, len(lines)):
    line = lines[i]
    
    if not line.strip():
        continue
    
    current_indent = len(line) - len(line.lstrip())
    
    if indent is None:
        indent = current_indent
    
    if current_indent < indent and line.strip() and not line.strip().startswith('-'):
        break
    
    if current_indent >= indent and re.match(r'^\s+-\s+', line):
        match = re.match(r'^\s+-\s+(.+)', line)
        if match:
            item = match.group(1).strip().strip('"').strip("'")
            print(item)
PYEOF
}

# 通配符模式匹配
match_pattern() {
    python3 "$MATCH_SCRIPT" "$1" "$2"
}

# 检查路径列表
check_paths() {
    local paths="$1"
    local check_func="$2"
    local IFS=$','
    read -ra ARR <<< "$paths"
    for path in "${ARR[@]}"; do
        "$check_func" "$path" || return 1
    done
    return 0
}

check_denylist() {
    local path="$1"
    local denylist
    denylist=$(parse_yaml "denylist")
    local IFS=$'\n'
    set -o noglob
    for pattern in $denylist; do
        [[ -z "$pattern" ]] && continue
        if match_pattern "$path" "$pattern"; then
            echo -e "${RED}✗ Denied: $path (pattern: $pattern)${NC}" >&2
            set +o noglob
            return 1
        fi
    done
    set +o noglob
    return 0
}

check_require_review() {
    local path="$1"
    local require_review
    require_review=$(parse_yaml "require-review")
    local violations=0
    local IFS=$'\n'
    set -o noglob
    for pattern in $require_review; do
        [[ -z "$pattern" ]] && continue
        if match_pattern "$path" "$pattern"; then
            echo -e "${YELLOW}⚠ Review: $path (pattern: $pattern)${NC}" >&2
            ((violations++))
        fi
    done
    set +o noglob
    return 0  # require-review 只是警告，不返回错误码
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
    local path="$1"
    local allowlist
    allowlist=$(parse_yaml "auto-merge-allowlist")
    local allowed=0
    local IFS=$'\n'
    set -o noglob
    for pattern in $allowlist; do
        [[ -z "$pattern" ]] && continue
        if match_pattern "$path" "$pattern"; then
            allowed=1 && break
        fi
    done
    set +o noglob
    [[ $allowed -eq 0 ]] && echo -e "${RED}✗ Not allowed: $path${NC}" >&2 && return 1
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
    check_paths "$paths" check_denylist || result=1
    echo -e "${GREEN}[2/4] Checking max-files...${NC}"
    check_max_files "$paths" || result=2
    echo -e "${GREEN}[3/4] Action-specific check...${NC}"
    case "$action" in
        auto-merge) check_paths "$paths" check_auto_merge || result=1 ;;
        auto-edit|check) check_paths "$paths" check_require_review || result=1 ;;
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

# 只在直接执行时运行 main
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
