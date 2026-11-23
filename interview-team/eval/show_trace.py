"""Компактна таблиця трасування: uv run python -m eval.show_trace runs/<час>/team_trace.json"""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", nargs="?", help="team_trace.json; типово — останній запуск"
    )
    args = parser.parse_args()
    path = (
        Path(args.path)
        if args.path
        else sorted(Path("runs").glob("*/team_trace.json"))[-1]
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"{path}\n{'t, s':>6}  {'author':<22} {'node':<26} route")
    for step in data["trace"]:
        if not step["node"]:
            continue
        print(
            f"{step['t']:>6}  {step['author']:<22} {step['node']:<26} {step['route'] or '-'}"
        )
    print(f"\nllm_calls: {data['llm_calls']}")
    print(f"tokens: {sum(data['tokens'].values())}, time: {data['seconds']} s")


if __name__ == "__main__":
    main()
