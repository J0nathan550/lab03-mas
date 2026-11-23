"""Експеримент на підмінній моделі: метрики обох систем і сліпі копії звітів."""

import asyncio
import json

from app.agent import build_workflow
from app.baseline import build_solo_agent
from eval.run_experiment import experiment
from tests.fixtures import AMBIGUITIES, ANSWERS, CONFLICT_REPORT, PLAN, REQUEST, script
from tests.scripted import ScriptedLlm

SOLO = "whole requirements analysis team"


def test_experiment_rows_and_blind_reports(tmp_path):
    team = ScriptedLlm(model="scripted", script=script())
    solo_reply = {
        "plan": PLAN,
        "answers": ANSWERS,
        "conflicts": CONFLICT_REPORT,
        "ambiguities": AMBIGUITIES,
    }
    solo = ScriptedLlm(model="scripted", script={SOLO: [solo_reply]})
    rows = asyncio.run(
        experiment(
            build_workflow(team),
            build_solo_agent(solo),
            [{"id": "R1", "request": REQUEST}],
            pause=0,
            out=tmp_path,
        )
    )
    by_system = {r["system"]: r for r in rows}
    assert by_system["team"]["llm_calls"] == 5 and by_system["solo"]["llm_calls"] == 1
    for row in rows:
        assert row["questions"] == 6 and row["closed_questions"] == 0
        assert row["conflicts"] == 1 and row["invalid_conflicts"] == 0
    key = json.loads((tmp_path / "blind_key.json").read_text())
    assert {k["system"] for k in key} == {"team", "solo"}
    for k in key:
        text = (tmp_path / "blind" / f"{k['code']}.md").read_text(encoding="utf-8")
        assert "## Рішення" not in text and "## Конфлікти вимог" in text
