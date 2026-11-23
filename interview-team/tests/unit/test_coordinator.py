"""Координатор: делегування, яке обирає модель (тут — сценарій)."""

import asyncio
from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.coordinator import build_coordinator
from run_cli import run_once


class CallingLlm(BaseLlm):
    """Координатор викликає interview_expert, експерт відповідає, координатор підсумовує."""

    turn: int = 0

    async def generate_content_async(
        self, llm_request, stream=False
    ) -> AsyncGenerator[LlmResponse, None]:
        instruction = str(llm_request.config.system_instruction or "")
        if "You are a requirements interview designer" in instruction:
            part = types.Part(text="- Як ви зараз записуєтеся до лікаря?")
        elif self.turn == 0:
            self.turn += 1
            part = types.Part(
                function_call=types.FunctionCall(
                    name="interview_expert",
                    args={"request": "Питання для пацієнта про запис до лікаря"},
                )
            )
        else:
            part = types.Part(text="Підсумок: питання для пацієнта підготовлено.")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def test_coordinator_delegates_to_one_expert():
    result = asyncio.run(
        run_once(
            build_coordinator(CallingLlm(model="scripted")),
            "Підготуй інтерв'ю з пацієнтом про онлайн-запис до лікаря.",
        )
    )
    authors = [s["author"] for s in result["trace"]]
    assert "interview_expert" in authors
    assert "stakeholder_expert" not in authors and "conflict_expert" not in authors
    assert result["trace"][-1]["text"].startswith("Підсумок")


def test_compare_counts_experts_per_repeat():
    from eval.compare_coordinator import REPEATS, compare

    rows = asyncio.run(
        compare(
            build_coordinator(CallingLlm(model="scripted")),
            [{"id": "R1", "request": "Підготуй інтерв'ю про онлайн-запис до лікаря."}],
            pause=0,
        )
    )
    assert len(rows) == REPEATS
    assert rows[0]["experts"] == "interview_expert"
