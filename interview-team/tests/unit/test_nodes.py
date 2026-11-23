"""Модульні тести детермінованих функцій."""

import pytest

from app.nodes import (
    conflict_issues,
    is_open_question,
    plural,
    question_issues,
    render_report,
)
from tests.fixtures import AMBIGUITIES, ANSWERS, APPROVE, CONFLICT_REPORT, PLAN


@pytest.mark.parametrize(
    "text",
    [
        "Як ви зараз записуєтеся до лікаря?",
        "У яких випадках прийом переносять?",
        "Розкажіть про останній запис до лікаря.",
        "Скільки пацієнтів ви приймаєте за зміну?",
    ],
)
def test_open_questions(text):
    assert is_open_question(text)


@pytest.mark.parametrize(
    "text",
    [
        "Чи зручно вам записуватися онлайн?",
        "Ви користуєтеся смартфоном?",
        "Що ви обираєте: так чи ні?",
        "Як ви записуєтеся",
    ],
)
def test_closed_questions(text):
    assert not is_open_question(text)


def test_question_issues_ok_for_valid_plan():
    assert question_issues(PLAN) == []


def test_question_issues_counts_and_stakeholders():
    plan = {
        "stakeholders": ["пацієнт", "лікар", "адміністратор"],
        "questions": [*PLAN["questions"][:4], {**PLAN["questions"][0], "id": "Q1"}],
    }
    issues = " ".join(question_issues(plan))
    assert "6-15 питань" in issues
    assert "повторюються" in issues
    assert "«адміністратор» має 0 питань" in issues


def test_conflict_issues():
    assert conflict_issues(CONFLICT_REPORT, ANSWERS) == []
    bad = {
        "conflicts": [
            {"id": "C1", "statement_a": "S2", "statement_b": "S2"},
            {"id": "C2", "statement_a": "S1", "statement_b": "S42"},
        ]
    }
    issues = conflict_issues(bad, ANSWERS)
    assert any("двічі" in i for i in issues) and any("S42" in i for i in issues)


def test_render_report_sections():
    report = render_report(
        {
            "plan": PLAN,
            "answers": ANSWERS,
            "conflicts": CONFLICT_REPORT,
            "ambiguities": AMBIGUITIES,
            "verdict": APPROVE,
            "drafts": 1,
            "stop_reason": "approved",
        }
    )
    for part in (
        "## пацієнт",
        "## лікар",
        "**Q2.**",
        "очікувана відповідь S2",
        "**C1** (S2 ↔ S5)",
        "«швидко»",
        "скасування запису",
        "APPROVE після 1",
    ):
        assert part in report


def test_plural_forms():
    forms = ("чернетки", "чернеток", "чернеток")
    assert plural(1, *forms) == "1 чернетки" and plural(3, *forms) == "3 чернеток"
    conflict = ("конфлікт", "конфлікти", "конфліктів")
    assert [plural(n, *conflict) for n in (1, 2, 5, 11, 21)] == [
        "1 конфлікт",
        "2 конфлікти",
        "5 конфліктів",
        "11 конфліктів",
        "21 конфлікт",
    ]


def test_render_report_for_single_agent():
    report = render_report(
        {
            "plan": PLAN,
            "answers": ANSWERS,
            "conflicts": CONFLICT_REPORT,
            "ambiguities": AMBIGUITIES,
            "drafts": 1,
            "stop_reason": "single call",
        }
    )
    assert (
        "Один агент, один виклик моделі" in report
        and "?" not in report.split("## Рішення")[1]
    )
