"""Експеримент: команда агентів проти одного агента на тих самих запитах.

uv run python -m eval.run_experiment            -> eval/results.csv, eval/reports/
"""

import asyncio
import csv
import json
import random
from pathlib import Path

from dotenv import load_dotenv

from app.nodes import conflict_issues, is_open_question, question_issues, render_report
from run_cli import run_once

HERE = Path(__file__).parent


def metrics(state: dict, result: dict) -> dict:
    """Детерміновані ознаки якості результату + вартість."""
    plan = state.get("plan") or {}
    questions = plan.get("questions", [])
    answers = state.get("answers") or {}
    conflicts = state.get("conflicts") or {}
    amb = state.get("ambiguities") or {}
    return {
        "stakeholders": len(plan.get("stakeholders", [])),
        "questions": len(questions),
        "closed_questions": sum(
            not is_open_question(q.get("text", "")) for q in questions
        ),
        "question_issues": len(question_issues(plan)) if plan else None,
        "statements": len(answers.get("statements", [])),
        "conflicts": len(conflicts.get("conflicts", [])),
        "invalid_conflicts": len(conflict_issues(conflicts, answers)),
        "ambiguities": len(amb.get("ambiguities", [])),
        "missing_topics": len(amb.get("missing_topics", [])),
        "drafts": state.get("drafts", 1),
        "stop_reason": state.get("stop_reason", "single call"),
        "llm_calls": sum(result["llm_calls"].values()),
        "tokens": sum(result["tokens"].values()),
        "seconds": result["seconds"],
    }


def blind_copy(state: dict) -> str:
    """Звіт для сліпої оцінки: без рядка «Рішення» і службових розділів."""
    report = render_report(
        {**state, "verdict": {}, "question_issues": [], "dropped_conflicts": []}
    )
    return report.split("\n## Рішення")[0]


async def experiment(
    team, solo, requests: list[dict], pause: float = 2.0, out: Path = HERE
) -> list[dict]:
    rows, blind = [], []
    for item in requests:
        for system, agent in (("team", team), ("solo", solo)):
            result = await run_once(agent, item["request"])
            state = result["state"]
            if system == "solo":
                state = state.get("solo") or {}
            rows.append({"id": item["id"], "system": system, **metrics(state, result)})
            blind.append((item["id"], system, blind_copy(state)))
            await asyncio.sleep(pause)  # пауза між запусками: ліміти API
    write_blind(blind, out)
    return rows


def write_blind(blind: list[tuple], here: Path = HERE) -> None:
    """Перемішує звіти під кодами B01..B10; ключ — в окремому файлі, не відкривати до оцінки."""
    out = here / "blind"
    out.mkdir(exist_ok=True)
    random.shuffle(blind)
    key = []
    for n, (req_id, system, text) in enumerate(blind, 1):
        code = f"B{n:02d}"
        (out / f"{code}.md").write_text(
            f"<!-- {req_id} -->\n{text}\n", encoding="utf-8"
        )
        key.append({"code": code, "id": req_id, "system": system})
    (here / "blind_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")


def main() -> None:
    from google.adk.models import Gemini
    from google.genai import types

    from app.agent import MODEL, build_workflow
    from app.baseline import build_solo_agent

    model = Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3))
    requests = json.loads((HERE / "requests.json").read_text(encoding="utf-8"))
    rows = asyncio.run(
        experiment(build_workflow(model), build_solo_agent(model), requests)
    )
    with open(HERE / "results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    load_dotenv()
    main()
