"""Координатор проти графа: 3 запити x 3 повтори координатора.

uv run python -m eval.compare_coordinator     -> eval/coordinator.csv
Граф для порівняння береться з eval/results.csv (рядки team для R1-R3).
"""

import asyncio
import csv
import json
from pathlib import Path

from dotenv import load_dotenv

from run_cli import run_once

HERE = Path(__file__).parent
EXPERTS = ("interview_expert", "stakeholder_expert", "conflict_expert")
REPEATS = 3


async def compare(coordinator, requests: list[dict], pause: float = 2.0) -> list[dict]:
    rows = []
    for item in requests:
        for repeat in range(1, REPEATS + 1):
            result = await run_once(coordinator, item["request"])
            called = sorted({s["author"] for s in result["trace"]} & set(EXPERTS))
            rows.append(
                {
                    "id": item["id"],
                    "repeat": repeat,
                    "experts": "+".join(called) or "-",
                    "llm_calls": sum(result["llm_calls"].values()),
                    "tokens": sum(result["tokens"].values()),
                    "seconds": result["seconds"],
                }
            )
            await asyncio.sleep(pause)
    return rows


def graph_rows(ids: set[str]) -> list[dict]:
    path = HERE / "results.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [
            r for r in csv.DictReader(f) if r["system"] == "team" and r["id"] in ids
        ]


def main() -> None:
    from google.adk.models import Gemini
    from google.genai import types

    from app.agent import MODEL
    from app.coordinator import build_coordinator

    model = Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3))
    requests = json.loads((HERE / "requests.json").read_text(encoding="utf-8"))[:3]
    rows = asyncio.run(compare(build_coordinator(model), requests))
    with open(HERE / "coordinator.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"{'id':<3} {'#':>1}  {'experts':<54} {'calls':>5} {'tokens':>7} {'s':>6}")
    for r in rows:
        print(
            f"{r['id']:<3} {r['repeat']:>1}  {r['experts']:<54} {r['llm_calls']:>5} "
            f"{r['tokens']:>7} {r['seconds']:>6}"
        )
    for item in requests:
        sets = {r["experts"] for r in rows if r["id"] == item["id"]}
        print(
            f"{item['id']}: вибір експертів {'стабільний' if len(sets) == 1 else 'змінювався'}"
        )
    graph = graph_rows({item["id"] for item in requests})
    if graph:
        print("\nГраф (eval/results.csv, team):")
        for r in graph:
            print(
                f"{r['id']:<3} calls {r['llm_calls']:>3}, tokens {r['tokens']:>6}, "
                f"s {r['seconds']:>6}, drafts {r['drafts']}, stop {r['stop_reason']}"
            )


if __name__ == "__main__":
    load_dotenv()
    main()
