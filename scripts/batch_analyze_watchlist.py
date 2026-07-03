#!/usr/bin/env python3
"""批量提交个股分析任务，并发=3，监控每只完成情况。"""

import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

API = "http://127.0.0.1:8000/api/v1"
CODES = [
    "688486",
    "002957",
    "002617",
    "300003",
    "300054",
    "601208",
    "300260",
    "688002",
    "603690",
    "300623",
]
CONCURRENCY = 3
POLL_INTERVAL = 6
MAX_POLLS = 80  # ~8 min per stock


def post_json(path: str, body: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get_json(path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
        return json.loads(r.read())


def submit(code: str) -> str:
    resp = post_json(
        "/analysis/analyze",
        {
            "stock_code": code,
            "report_type": "detailed",
            "async_mode": True,
            "analysis_phase": "auto",
        },
    )
    return resp["task_id"]


def wait_task(task_id: str, code: str) -> dict[str, Any]:
    t0 = time.time()
    for i in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        s = get_json(f"/analysis/status/{task_id}")
        st = s.get("status")
        prog = s.get("progress", 0)
        if st in ("completed", "success", "failed"):
            dt = time.time() - t0
            return {
                "code": code,
                "task_id": task_id,
                "status": st,
                "progress": prog,
                "elapsed_s": round(dt),
                "result": s,
            }
        if i % 4 == 0:
            print(
                f"  [{code}] {st} {prog}%  elapsed={int(time.time() - t0)}s", flush=True
            )
    return {
        "code": code,
        "task_id": task_id,
        "status": "timeout",
        "elapsed_s": MAX_POLLS * POLL_INTERVAL,
        "result": None,
    }


def main():
    print(f"=== 批量分析 {len(CODES)} 只股票，并发={CONCURRENCY} ===")
    print(f"股票: {CODES}\n")
    t_all0 = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        # 阶段1: 全部提交
        submit_fut = {ex.submit(submit, c): c for c in CODES}
        tasks: dict[str, str] = {}
        for f in as_completed(submit_fut):
            c = submit_fut[f]
            try:
                tid = f.result()
                tasks[c] = tid
                print(f"[SUBMIT] {c} -> {tid}", flush=True)
            except Exception as e:
                print(f"[SUBMIT-FAIL] {c}: {e}", flush=True)

        print(f"\n--- 全部提交完成，开始监控 ({len(tasks)} 个任务) ---\n")
        # 阶段2: 监控完成
        wait_fut = {ex.submit(wait_task, tid, c): c for c, tid in tasks.items()}
        results = []
        for f in as_completed(wait_fut):
            c = wait_fut[f]
            try:
                r = f.result()
                results.append(r)
                tag = "OK" if r["status"] in ("completed", "success") else "FAIL"
                print(
                    f"\n[{tag}] {c} status={r['status']} elapsed={r['elapsed_s']}s",
                    flush=True,
                )
                if r.get("result", {}).get("result"):
                    res = r["result"]["result"]
                    if "stock_name" in res:
                        print(f"     名称: {res['stock_name']}", flush=True)
                    if "summary" in res:
                        print(
                            f"     摘要: {res['summary'].get('analysis_summary', '')[:100]}",
                            flush=True,
                        )
            except Exception as e:
                print(f"[WAIT-FAIL] {c}: {e}", flush=True)

    print(f"\n=== 全部完成 总耗时 {int(time.time() - t_all0)}s ===")
    ok = sum(1 for r in results if r["status"] in ("completed", "success"))
    fail = sum(1 for r in results if r["status"] not in ("completed", "success"))
    print(f"成功: {ok}  失败: {fail}")
    for r in sorted(results, key=lambda x: x["code"]):
        print(f"  {r['code']}: {r['status']} ({r['elapsed_s']}s)")


if __name__ == "__main__":
    main()
