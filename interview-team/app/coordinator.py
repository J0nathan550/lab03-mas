"""Альтернативна архітектура: координатор сам вирішує, кого з експертів залучити.

На відміну від графа маршрут тут обирає LLM під час виконання.
"""

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from .agents import LANGUAGE


def build_coordinator(model: BaseLlm | str) -> Agent:
    def expert(name: str, description: str, focus: str) -> Agent:
        return Agent(
            name=name,
            model=model,
            description=description,
            mode="single_turn",
            instruction=f"You are a {focus}. Answer the delegated request briefly "
            f"and concretely, max 8 bullet points. {LANGUAGE}",
        )

    experts = [
        expert(
            "interview_expert",
            "Designs open-ended requirements interview questions for stakeholders.",
            "requirements interview designer",
        ),
        expert(
            "stakeholder_expert",
            "Predicts how each stakeholder would answer and what they care about.",
            "stakeholder simulator who speaks for every role",
        ),
        expert(
            "conflict_expert",
            "Finds contradictions and vague terms in stakeholder needs.",
            "requirements conflict and ambiguity analyst",
        ),
    ]
    return Agent(
        name="coordinator",
        model=model,
        instruction=f"""
You coordinate a team of experts: interview_expert, stakeholder_expert, conflict_expert.
The user wants to prepare a requirements interview for the described project.
Call only the experts whose competence is needed, pass each of them a focused
request, then merge their answers into one interview script: questions per
stakeholder, expected conflicts with clarifying questions, vague terms.
Do not answer expert questions yourself. Call each expert at most once.
{LANGUAGE}
""",
        sub_agents=experts,
    )
