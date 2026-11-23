"""Мультиагентна система «Підготовка інтерв'ю з вимог» на графі ADK 2.x."""

import os

from google.adk import Workflow
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.workflow import JoinNode
from google.genai import types

from .agents import build_agents
from .nodes import (
    conflict_check,
    gate,
    intake,
    publish,
    question_check,
    reject,
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def build_workflow(model: BaseLlm | str) -> Workflow:
    a = build_agents(model)
    findings = JoinNode(name="findings")  # чекає на обидві паралельні гілки
    return Workflow(
        name="interview_team",
        max_concurrency=2,  # не більше двох агентів одночасно
        edges=[
            ("START", intake),
            (intake, {"ok": a["designer"], "reject": reject}),
            (a["designer"], question_check),
            (question_check, {"ok": a["simulator"], "fix": a["designer"]}),
            (a["simulator"], (a["conflicts"], a["ambiguity"])),
            (a["conflicts"], conflict_check),
            (conflict_check, {"ok": findings, "fix": a["conflicts"]}),
            (a["ambiguity"], findings),
            (findings, a["lead"], gate),
            (gate, {"revise": a["designer"], "publish": publish}),
        ],
    )


root_agent = build_workflow(
    Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3))
)

app = App(root_agent=root_agent, name="app")
