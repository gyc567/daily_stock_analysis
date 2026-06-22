# -*- coding: utf-8 -*-
"""郑希投研检索召回机械验证。

对 ``data/fund_manager_views/zhengxi/golden_questions.json`` 里带
``retrieval_keywords`` 的问题，跑 ``corpus.search_corpus``（含同义词扩展），
验证召回数 >= ``min_retrieval_hits``。不调用 LLM，只验证检索层质量。

用法::

    python scripts/check_zhengxi_retrieval.py
"""

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.services.zhengxi import corpus  # noqa: E402

GOLDEN_PATH = os.path.join(ROOT, "data", "fund_manager_views", "zhengxi", "golden_questions.json")


def main() -> int:
    with open(GOLDEN_PATH, encoding="utf-8") as fh:
        golden = json.load(fh)

    checked = 0
    passed = 0
    failures: list[str] = []

    for question in golden.get("questions", []):
        keywords = question.get("retrieval_keywords") or []
        if not keywords:
            continue
        checked += 1
        hits = corpus.search_corpus(keywords, max_results=20)
        min_hits = question.get("min_retrieval_hits", 1)
        sample = hits[0] if hits else None
        sample_src = (
            f"[{sample['date']} | {sample['type']} | {sample['title'][:24]}]"
            if sample
            else "(无命中)"
        )
        status = "OK" if len(hits) >= min_hits else "FAIL"
        print(f"  [{status}] {question['id']} {question['prompt'][:30]}")
        print(f"         keywords={keywords} hits={len(hits)} >= {min_hits}  首条={sample_src}")
        if len(hits) >= min_hits:
            passed += 1
        else:
            failures.append(f"{question['id']} ({question['prompt'][:20]}): {len(hits)} < {min_hits}")

    print("\n" + "=" * 50)
    print(f"检索召回验证: {passed}/{checked} 通过")
    if failures:
        print("FAIL:")
        for fail in failures:
            print(f"  - {fail}")
        return 1
    print("OK: 所有溯源类问题召回达标")
    return 0


if __name__ == "__main__":
    sys.exit(main())
