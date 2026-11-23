"""Контракти даних між агентами: кожен агент повертає JSON за схемою."""

from typing import Literal

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str = Field(description="Unique question id: Q1, Q2, ...")
    stakeholder: str = Field(description="Stakeholder role this question is asked to")
    text: str = Field(
        description="Open-ended interview question that starts with an "
        "interrogative word (Що, Як, Які, Чому, Коли, Хто, Де, Скільки) or with "
        "Розкажіть/Опишіть; never a yes/no question that starts with 'Чи'"
    )
    goal: str = Field(description="Which requirement information the question elicits")


class InterviewPlan(BaseModel):
    topic: str = Field(
        description="Short name of the system or feature under discussion"
    )
    stakeholders: list[str] = Field(description="2-4 stakeholder roles to interview")
    questions: list[Question] = Field(
        description="6-15 questions, at least 2 for every stakeholder; key topics "
        "are asked to several stakeholders so their views can be compared"
    )


class Statement(BaseModel):
    id: str = Field(description="Unique statement id: S1, S2, ...")
    stakeholder: str = Field(description="Stakeholder role who says it")
    question_id: str = Field(description="Id of the question this statement answers")
    text: str = Field(description="Simulated answer in the first person, 1-3 sentences")


class SimulatedAnswers(BaseModel):
    statements: list[Statement] = Field(
        description="Exactly one statement per question of the interview plan"
    )


class Conflict(BaseModel):
    id: str = Field(description="Unique conflict id: C1, C2, ...")
    statement_a: str = Field(
        description="Id of the first conflicting statement, e.g. S2"
    )
    statement_b: str = Field(
        description="Id of the second conflicting statement, e.g. S7"
    )
    description: str = Field(description="What exactly contradicts what")
    clarifying_question: str = Field(
        description="Open question that helps to resolve the conflict in the interview"
    )


class ConflictReport(BaseModel):
    conflicts: list[Conflict] = Field(
        description="0-5 contradictions between statements; each cites two statements"
    )


class Ambiguity(BaseModel):
    statement_id: str = Field(description="Id of the statement with a vague term")
    term: str = Field(description="Vague word or phrase, e.g. 'швидко', 'зручно'")
    clarifying_question: str = Field(
        description="Open question that turns the term into a measurable requirement"
    )


class AmbiguityReport(BaseModel):
    ambiguities: list[Ambiguity] = Field(
        description="0-6 vague terms in the statements"
    )
    missing_topics: list[str] = Field(
        description="0-3 uncovered topics critical for the first release"
    )


class Verdict(BaseModel):
    decision: Literal["APPROVE", "REVISE"]
    comments: list[str] = Field(
        description="Up to 5 specific changes the question designer must make"
    )
