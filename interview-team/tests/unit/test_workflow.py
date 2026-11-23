"""Тести оркестрації графа на підмінній моделі."""

import asyncio

from app.agent import build_workflow
from app.nodes import MAX_DRAFTS
from run_cli import run_once
from tests.fixtures import (
    AMBIGUITY,
    APPROVE,
    BAD_CONFLICTS,
    CONFLICTS,
    DESIGNER,
    LEAD,
    PLAN,
    REQUEST,
    REVISE,
    SIMULATOR,
    script,
)
from tests.scripted import ScriptedLlm


def run(scenario, request=REQUEST):
    model = ScriptedLlm(model="scripted", script=scenario)
    return asyncio.run(run_once(build_workflow(model), request)), model


def test_approved_on_first_round():
    result, model = run(script())
    state = result["state"]
    assert state["stop_reason"] == "approved" and state["drafts"] == 1
    assert "## Конфлікти вимог" in state["report"] and "S2 ↔ S5" in state["report"]
    assert sorted(model.calls) == sorted(
        [DESIGNER, SIMULATOR, CONFLICTS, AMBIGUITY, LEAD]
    )


def test_parallel_branches_meet_in_join():
    result, _ = run(script())
    nodes = [step["node"] for step in result["trace"]]
    join = nodes.index("findings@1")
    assert (
        nodes.index("conflict_check@1") < join
        and nodes.index("ambiguity_analyst@1") < join
    )
    assert join < nodes.index("analyst_lead@1")


def test_revise_loop_then_approve():
    result, model = run(script(designer=[PLAN, PLAN], lead=[REVISE, APPROVE]))
    assert result["state"]["drafts"] == 2
    assert model.calls.count(DESIGNER) == 2 and model.calls.count(LEAD) == 2


def test_loop_is_bounded():
    result, model = run(script(lead=[REVISE]))
    assert result["state"]["stop_reason"] == "max_drafts"
    assert model.calls.count(LEAD) == MAX_DRAFTS
    assert "Невиконані зауваження" in result["state"]["report"]


def test_closed_questions_go_back_without_other_agents():
    closed = {
        **PLAN,
        "questions": [
            {**PLAN["questions"][0], "text": "Чи зручно вам дзвонити?"},
            *PLAN["questions"][1:],
        ],
    }
    result, model = run(script(designer=[closed, PLAN]))
    assert model.calls[:2] == [DESIGNER, DESIGNER]
    routes = {step["node"]: step["route"] for step in result["trace"] if step["route"]}
    assert routes["question_check@1"] == "fix" and routes["question_check@2"] == "ok"
    assert result["state"]["stop_reason"] == "approved"


def test_conflict_without_two_statements_is_returned_then_dropped():
    result, model = run(script(conflicts=[BAD_CONFLICTS]))
    state = result["state"]
    assert model.calls.count(CONFLICTS) == 2
    assert state["conflicts"] == {"conflicts": []}
    assert "S99" in state["report"]


def test_short_request_is_rejected_without_llm():
    result, model = run({}, request="запис до лікаря")
    assert model.calls == []
    assert any("Запит відхилено" in step["text"] for step in result["trace"])


def test_designer_revises_previous_draft():
    """Регресія з трасувань v1: без попередньої чернетки дизайнер губив додані питання."""
    _, model = run(script(designer=[PLAN, PLAN], lead=[REVISE, APPROVE]))
    designer = [
        p for c, p in zip(model.calls, model.prompts, strict=True) if c == DESIGNER
    ]
    lead = [p for c, p in zip(model.calls, model.prompts, strict=True) if c == LEAD]
    assert "Як ви зараз записуєтеся до лікаря?" not in designer[0]
    assert "Як ви зараз записуєтеся до лікаря?" in designer[1]
    assert "додай питання про скасування запису" in designer[1]
    assert "додай питання про скасування запису" in lead[1]
