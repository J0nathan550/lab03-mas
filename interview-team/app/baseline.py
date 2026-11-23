"""Базова лінія: один агент виконує роботу всієї команди за один виклик."""

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm
from pydantic import BaseModel

from .agents import LANGUAGE
from .schemas import AmbiguityReport, ConflictReport, InterviewPlan, SimulatedAnswers


class SoloResult(BaseModel):
    plan: InterviewPlan
    answers: SimulatedAnswers
    conflicts: ConflictReport
    ambiguities: AmbiguityReport


def build_solo_agent(model: BaseLlm | str) -> Agent:
    return Agent(
        name="solo",
        model=model,
        instruction=f"""
You are a whole requirements analysis team in one person. For the project description:
1) choose 2-4 stakeholder roles and write 6-15 open-ended interview questions
   (start with Що, Як, Які, Чому, Коли, Хто, Де, Скільки, Розкажіть or Опишіть,
   never with "Чи"), at least 2 for every stakeholder, ids Q1, Q2, ...;
2) simulate exactly one first-person answer per question, ids S1, S2, ...;
3) find 0-5 contradictions between the answers, each citing two different
   statement ids, with an open clarifying question;
4) list 0-6 vague terms (statement id, term, clarifying question) and 0-3
   uncovered topics critical for the first release.
{LANGUAGE}
""",
        output_schema=SoloResult,
        output_key="solo",
    )
