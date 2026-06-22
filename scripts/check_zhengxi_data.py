# -*- coding: utf-8 -*-
"""校验郑希投研数据完整性。

用法::

    python scripts/check_zhengxi_data.py

检查项：核心文件存在、语料文档数与格式、corpus_index 一致性、
8 只基金快照齐全且 JSON 可解析。
"""

import glob
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 老版本 Python 无此方法
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "fund_manager_views", "zhengxi")
CORPUS = os.path.join(DATA, "corpus")
FUND = os.path.join(DATA, "fund_data")

errors: list[str] = []
warnings: list[str] = []


def main() -> int:
    # 1. 核心文件
    for fn in ("method.md", "scorecard.md", "corpus_index.json"):
        if not os.path.exists(os.path.join(DATA, fn)):
            errors.append(f"缺失核心文件: {fn}")

    # 2. 语料
    all_md = sorted(glob.glob(os.path.join(CORPUS, "**", "*.md"), recursive=True))
    doc_md = [
        p for p in all_md
        if any(t in p for t in ("定期报告", "基金经理手记", "媒体报道"))
    ]
    print(f"[corpus] 文档 markdown: {len(doc_md)} 篇")
    if len(doc_md) < 70:
        errors.append(f"语料文档数 {len(doc_md)} 偏少（预期 ~76）")

    no_title = no_date = 0
    for path in doc_md:
        text = open(path, encoding="utf-8").read()
        if not re.search(r"^#\s+", text, re.M):
            no_title += 1
        if "日期" not in text:
            no_date += 1
    if no_title:
        errors.append(f"{no_title} 篇语料缺一级标题")
    if no_date:
        warnings.append(f"{no_date} 篇语料缺日期字段")

    # 3. corpus_index 一致性
    idx_path = os.path.join(DATA, "corpus_index.json")
    if os.path.exists(idx_path):
        with open(idx_path, encoding="utf-8") as fh:
            idx = json.load(fh)
        docs = idx.get("documents", [])
        print(f"[corpus_index] 索引文档: {len(docs)} 条")
        if abs(len(docs) - len(doc_md)) > 5:
            warnings.append(
                f"索引文档数 {len(docs)} 与实际 md {len(doc_md)} 差异较大"
            )

    # 4. 基金数据
    fidx_path = os.path.join(FUND, "_index.json")
    if not os.path.exists(fidx_path):
        errors.append("缺失 fund_data/_index.json")
    else:
        with open(fidx_path, encoding="utf-8") as fh:
            fidx = json.load(fh)
        funds = fidx.get("funds", [])
        print(f"[fund_data] 基金: {len(funds)} 只")
        if len(funds) != 8:
            warnings.append(f"基金数 {len(funds)}（预期 8）")
        for fund in funds:
            dirname = os.path.basename(fund["dir"])
            fund_dir = os.path.join(FUND, dirname)
            if not os.path.isdir(fund_dir):
                errors.append(f"基金目录缺失: {dirname}")
                continue
            for fn in ("季度持仓.json", "净值业绩规模.json"):
                path = os.path.join(fund_dir, fn)
                if not os.path.exists(path):
                    errors.append(f"缺失 {fn}: {dirname}")
                    continue
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                except Exception as exc:
                    errors.append(f"JSON 解析失败 {dirname}/{fn}: {exc}")
                    continue
                if fn == "季度持仓.json" and not (isinstance(data, list) and data):
                    errors.append(f"季度持仓为空: {dirname}")
                elif fn == "净值业绩规模.json" and not isinstance(data, dict):
                    errors.append(f"净值业绩非对象: {dirname}")

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
    print("OK: 郑希投研数据校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
