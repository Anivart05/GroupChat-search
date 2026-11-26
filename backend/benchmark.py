"""Benchmark runner shared by evaluate.py and the /api/benchmark endpoint."""
from __future__ import annotations

from collections import defaultdict


def run_benchmark(engine, queries: list[dict]) -> dict:
    rows = []
    for q in queries:
        res = engine.search(q["query"], top_k=5, context_window=0)
        ids = [h["message"]["id"] for h in res["hits"]]
        rank = next((i + 1 for i, mid in enumerate(ids) if mid in q["expected_ids"]), None)
        rows.append({
            "id": q["id"], "query": q["query"], "shape": q["shape"],
            "zero_overlap": q["zero_overlap"], "expected_ids": q["expected_ids"],
            "rank": rank, "top_hit": res["hits"][0]["message"]["text"] if res["hits"] else None,
        })

    def stats(sub):
        n = len(sub)
        if not n:
            return {"n": 0, "top1": 0, "recall5": 0, "mrr": 0}
        return {
            "n": n,
            "top1": sum(1 for r in sub if r["rank"] == 1),
            "recall5": sum(1 for r in sub if r["rank"]),
            "mrr": round(sum(1 / r["rank"] for r in sub if r["rank"]) / n, 4),
        }

    by_shape = defaultdict(list)
    for r in rows:
        by_shape[r["shape"]].append(r)
    return {
        "overall": stats(rows),
        "zero_overlap": stats([r for r in rows if r["zero_overlap"]]),
        "by_shape": {k: stats(v) for k, v in by_shape.items()},
        "rows": rows,
    }
