"""LLM-агенти команди. Модель передається параметром: у тестах її підміняють."""

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from .schemas import (
    AmbiguityReport,
    ConflictReport,
    InterviewPlan,
    SimulatedAnswers,
    Verdict,
)

LANGUAGE = "Write all text values in Ukrainian."


def build_agents(model: BaseLlm | str) -> dict[str, Agent]:
    designer = Agent(
        name="question_designer",
        model=model,
        description="Designs open-ended requirements interview questions.",
        instruction=f"""
You are a requirements interview designer.
The project description from the user is given as input; it is repeated here: {{request}}
Choose 2-4 stakeholder roles and write 6-15 interview questions, at least 2 for
every stakeholder. Every question is open-ended: it starts with Що, Як, Які,
Який, Чому, Коли, Хто, Де, Скільки, Розкажіть or Опишіть and never with "Чи".
Ask about the same key topics (priorities, deadlines, data, access) several
stakeholders, so their views can be compared later.
Do not answer the questions and do not invent facts about the project.
Your previous draft (empty on the first draft): {{plan?}}
Feedback on the previous draft (empty on the first draft): {{feedback?}}
If there is a previous draft, revise it instead of starting over: keep the
questions that already work, keep the questions added in earlier rounds and
apply every comment of the feedback.
{LANGUAGE}
""",
        output_schema=InterviewPlan,
        output_key="plan",
    )
    simulator = Agent(
        name="stakeholder_simulator",
        model=model,
        description="Simulates stakeholder answers to the interview questions.",
        instruction=f"""
You simulate the stakeholders of a software project in a requirements interview.
Interview plan: {{plan}}
Write exactly one statement per question, in the first person, in the voice of
the stakeholder the question is addressed to, 1-3 sentences each. Number the
statements S1, S2, ... in the order of questions. Stakeholders have their own
interests, so realistic answers may disagree with each other. Do not add
questions and do not comment on the answers.
{LANGUAGE}
""",
        output_schema=SimulatedAnswers,
        output_key="answers",
    )
    conflicts = Agent(
        name="conflict_detector",
        model=model,
        description="Finds contradictions between stakeholder statements.",
        instruction=f"""
You are a requirements conflict detector.
Statements: {{answers}}
Find 0-5 contradictions between statements. Every conflict cites exactly two
different existing statement ids (statement_a, statement_b) and gives an open
clarifying question for the interviewer. Report only real contradictions that
follow from the statements; if there are none, return an empty list.
Problems with your previous answer (empty on the first try): {{conflict_feedback?}}
{LANGUAGE}
""",
        output_schema=ConflictReport,
        output_key="conflicts",
    )
    ambiguity = Agent(
        name="ambiguity_analyst",
        model=model,
        description="Finds vague terms and missing requirement topics.",
        instruction=f"""
You are a requirements ambiguity analyst.
Project description: {{request}}
Statements: {{answers}}
List 0-6 vague terms in the statements ("швидко", "зручно", "багато", "безпечно")
with the statement id and an open question that makes the term measurable.
List 0-3 topics the interview does not cover at all and that are critical
for the first release of the described project.
Do not look for contradictions: another agent does it.
{LANGUAGE}
""",
        output_schema=AmbiguityReport,
        output_key="ambiguities",
    )
    lead = Agent(
        name="analyst_lead",
        model=model,
        description="Accepts the interview script or sends it back with comments.",
        instruction=f"""
You are the lead business analyst. Decide whether the interview script is ready.
Project description: {{request}}
Interview plan: {{plan}}
Simulated statements: {{answers}}
Conflicts: {{conflicts}}
Ambiguities and missing topics: {{ambiguities}}
Your comments on the previous draft (empty on the first review): {{lead_comments?}}
Return APPROVE if every stakeholder has at least 2 questions, your previous
comments are addressed and no missing topic blocks the first release described
in the project description. Topics outside that scope are not a reason to
revise. Otherwise return REVISE with at most 3 specific comments for the
question designer (which questions to add, remove or rephrase); do not repeat
comments that are already addressed. Do not write the questions yourself.
{LANGUAGE}
""",
        output_schema=Verdict,
        output_key="verdict",
    )
    return {
        "designer": designer,
        "simulator": simulator,
        "conflicts": conflicts,
        "ambiguity": ambiguity,
        "lead": lead,
    }
