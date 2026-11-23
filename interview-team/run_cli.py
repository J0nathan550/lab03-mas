"""Запуск системи з термінала зі збереженням звіту і трасування.

uv run python run_cli.py "опис проєкту і стейкхолдерів" [--mode team|solo|coordinator]
"""

import argparse
import asyncio
import json
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Workflow
from google.adk.runners import InMemoryRunner
from google.genai import types

APP_NAME = "interview_team"


async def run_once(agent, request: str) -> dict:
    """Виконує агента або граф один раз і повертає стан, трасування і метрики."""
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id="student"
    )
    trace, calls, tokens = [], defaultdict(int), defaultdict(int)
    started = time.perf_counter()
    message = types.Content(role="user", parts=[types.Part(text=request)])
    async for event in runner.run_async(
        user_id="student", session_id=session.id, new_message=message
    ):
        text = ""
        if event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts)
            for part in event.content.parts:
                call = part.function_call
                if call and not text:
                    text = (
                        f"-> {call.name}({json.dumps(call.args, ensure_ascii=False)})"
                    )
        route = event.actions.route if event.actions else None
        # Події вузлів-функцій мають автором сам граф; їх не рахуємо як виклики LLM
        from_model = (
            text
            and event.author != "user"
            and not (isinstance(agent, Workflow) and event.author == agent.name)
        )
        if event.usage_metadata or from_model:
            calls[event.author] += 1
        if event.usage_metadata:
            tokens[event.author] += event.usage_metadata.total_token_count or 0
        node = (event.node_info.path or "") if event.node_info else ""
        trace.append(
            {
                "t": round(time.perf_counter() - started, 2),
                "author": event.author,
                "node": node.split("/")[-1],
                "route": route,
                "text": text[:300],
            }
        )
    session = await runner.session_service.get_session(
        app_name=APP_NAME, user_id="student", session_id=session.id
    )
    assert session is not None
    return {
        "state": dict(session.state),
        "trace": trace,
        "llm_calls": dict(calls),
        "tokens": dict(tokens),
        "seconds": round(time.perf_counter() - started, 2),
    }


def main() -> None:
    from google.adk.models import Gemini

    from app.agent import MODEL, build_workflow
    from app.baseline import build_solo_agent
    from app.coordinator import build_coordinator
    from app.nodes import render_report

    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    parser.add_argument(
        "--mode", choices=["team", "solo", "coordinator"], default="team"
    )
    args = parser.parse_args()

    model = Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3))
    builders = {
        "team": build_workflow,
        "solo": build_solo_agent,
        "coordinator": build_coordinator,
    }
    result = asyncio.run(run_once(builders[args.mode](model), args.request))
    if args.mode == "coordinator":
        for step in result["trace"]:
            print(f"{step['t']:>6}s {step['author']:<20} {step['text'][:90]!r}")
        print(
            f"\nLLM calls: {result['llm_calls']}, "
            f"tokens: {sum(result['tokens'].values())}, time: {result['seconds']} s"
        )
        return

    state = result["state"]
    if args.mode == "solo" and "solo" in state:
        state = {**state["solo"], "drafts": 1, "stop_reason": "single call"}
    if args.mode == "team" and "request" not in state:
        report = next(s["text"] for s in reversed(result["trace"]) if s["text"])
    else:
        report = state.get("report") or render_report(state)
    print(report)
    print(
        f"\n[{args.mode}] LLM calls: {result['llm_calls']}, "
        f"tokens: {sum(result['tokens'].values())}, time: {result['seconds']} s"
    )

    out = Path("runs") / time.strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.mode}_report.md").write_text(report, encoding="utf-8")
    (out / f"{args.mode}_trace.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"saved: {out}")


if __name__ == "__main__":
    load_dotenv()
    main()
