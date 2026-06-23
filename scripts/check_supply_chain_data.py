# -*- coding: utf-8 -*-
"""校验供应链分析 skill 数据完整性。

用法::

    python scripts/check_supply_chain_data.py

检查项：SKILL.md、核心 5 个 references、scorecard 可 import、
assets/evals/examples 齐全。末尾打印 scorecard 输入 schema（供打分工具参考）。
"""

import importlib.util
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "supply_chain_skill")

CORE_REFS = [
    "deep-research-workflow",
    "evidence-ladder",
    "market-source-playbook",
    "serenity-dialogue-protocol",
    "output-style-and-language",
]

errors: list[str] = []
warnings: list[str] = []


def main() -> int:
    # SKILL.md
    skill_path = os.path.join(DATA, "SKILL.md")
    if not os.path.exists(skill_path):
        errors.append("缺失 SKILL.md")
    else:
        lines = open(skill_path, encoding="utf-8").read().count("\n")
        print(f"[SKILL.md] {lines} 行")
        if lines < 100:
            warnings.append("SKILL.md 偏短")

    # 核心 5 references
    missing_refs = [
        ref for ref in CORE_REFS
        if not os.path.exists(os.path.join(DATA, "references", f"{ref}.md"))
    ]
    if missing_refs:
        errors.append(f"缺失核心 references: {missing_refs}")
    print(f"[references] 核心 5 个: {'OK' if not missing_refs else '缺失 ' + str(missing_refs)}")

    # scorecard 可 import（纯函数库）
    scorecard_path = os.path.join(DATA, "scripts", "serenity_scorecard.py")
    if not os.path.exists(scorecard_path):
        errors.append("缺失 scripts/serenity_scorecard.py")
    else:
        try:
            spec = importlib.util.spec_from_file_location(
                "serenity_scorecard", scorecard_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            assert hasattr(module, "score") and hasattr(module, "to_markdown")
            print("[scorecard] import OK（score + to_markdown 纯函数）")
        except Exception as exc:
            errors.append(f"scorecard import 失败: {exc}")

    # assets / evals / examples
    for required in ("assets/bottleneck-scorecard.json", "evals/test-cases.md"):
        if not os.path.exists(os.path.join(DATA, required)):
            errors.append(f"缺失 {required}")
    examples_dir = os.path.join(DATA, "examples")
    if not os.path.isdir(examples_dir) or not os.listdir(examples_dir):
        errors.append("缺失 examples（输出样例）")

    # 打印 scorecard 输入 schema（阶段 1 打分工具用）
    template_path = os.path.join(DATA, "assets", "bottleneck-scorecard.json")
    if os.path.exists(template_path):
        try:
            template = json.load(open(template_path, encoding="utf-8"))
            print(f"[scorecard schema] 顶层 keys: {list(template.keys())}")
        except Exception as exc:
            warnings.append(f"bottleneck-scorecard.json 解析失败: {exc}")

    print("\n" + "=" * 50)
    if errors:
        print(f"FAIL: {len(errors)} 个错误")
        for err in errors:
            print(f"  - {err}")
        return 1
    if warnings:
        print(f"WARN: {len(warnings)} 个警告（不阻断）")
        for warn in warnings:
            print(f"  - {warn}")
    print("OK: 供应链 skill 数据校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
