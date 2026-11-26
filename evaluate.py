"""Run the 40-query benchmark:  python evaluate.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from benchmark import run_benchmark  # noqa: E402
from search_engine import SearchEngine  # noqa: E402


def main() -> None:
    messages = json.loads((ROOT / "data" / "chat_messages.json").read_text(encoding="utf-8"))
    queries = json.loads((ROOT / "data" / "test_queries.json").read_text(encoding="utf-8"))
    engine = SearchEngine(messages)
    res = run_benchmark(engine, queries)

    people = engine.participants
    print("=" * 78)
    print("SEARCH A GROUP CHAT PROPERLY - BENCHMARK")
    print("=" * 78)
    print(f"Messages: {len(messages):,} | Participants: {len(people)} ({', '.join(people)})")
    print(f"Span: {engine.messages[0]['timestamp']} -> {engine.messages[-1]['timestamp']}")
    o, z = res["overall"], res["zero_overlap"]
    print(f"\nQueries:            {o['n']}")
    print(f"Top-1:              {o['top1']}/{o['n']} ({o['top1'] / o['n']:.1%})")
    print(f"Recall@5:           {o['recall5']}/{o['n']} ({o['recall5'] / o['n']:.1%})")
    print(f"MRR:                {o['mrr']}")
    print(f"Zero-overlap R@5:   {z['recall5']}/{z['n']}   (Top-1: {z['top1']}/{z['n']})")
    print("\nBy query shape:")
    for shape, s in res["by_shape"].items():
        print(f"  {shape:<11} n={s['n']:<3} top1={s['top1']:<3} recall@5={s['recall5']:<3} mrr={s['mrr']}")
    misses = [r for r in res["rows"] if r["rank"] != 1]
    if misses:
        print("\nNot ranked #1:")
        for r in misses:
            print(f"  {r['id']} rank={r['rank']}  {r['query']!r}\n       got: {r['top_hit']!r}")
    print("=" * 78)


if __name__ == "__main__":
    main()
