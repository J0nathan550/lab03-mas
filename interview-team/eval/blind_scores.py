"""Зведення сліпої оцінки: uv run python -m eval.blind_scores

Спочатку оціни eval/blind/B01..B10.md у файлі eval/blind_scores.csv (code,score,comment;
score 0-2), не відкриваючи eval/blind_key.json. Скрипт розкриває ключ і рахує середні.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent


def main() -> None:
    key = {k["code"]: k for k in json.loads((HERE / "blind_key.json").read_text())}
    with open(HERE / "blind_scores.csv", encoding="utf-8") as f:
        scores = list(csv.DictReader(f))
    missing = [
        r["code"] for r in scores if (r["score"] or "").strip() not in ("0", "1", "2")
    ]
    if missing:
        print("Не оцінено (потрібно 0, 1 або 2): " + ", ".join(missing))
        return
    by_system = defaultdict(list)
    print(f"{'code':<5} {'id':<3} {'system':<6} score  comment")
    for row in sorted(
        scores, key=lambda r: (key[r["code"]]["id"], key[r["code"]]["system"])
    ):
        k = key[row["code"]]
        by_system[k["system"]].append(int(row["score"]))
        print(
            f"{row['code']:<5} {k['id']:<3} {k['system']:<6} {row['score']:>5}  {row['comment']}"
        )
    for system, values in sorted(by_system.items()):
        print(
            f"\n{system}: середня якість {sum(values) / len(values):.1f} з 2 ({len(values)} звітів)"
        )


if __name__ == "__main__":
    main()
