"""Детерміновані вузли графа: перевірки і маршрутизація без LLM."""

import re

from google.adk import Context, Event

MAX_DRAFTS = 3  # скільки разів дизайнер може переписати набір питань
MAX_CONFLICT_FIXES = 1  # скільки разів детектор конфліктів може виправити посилання
MIN_REQUEST_CHARS = 30
MAX_REQUEST_CHARS = 2000
MIN_QUESTIONS, MAX_QUESTIONS = 6, 15
MIN_STAKEHOLDERS, MAX_STAKEHOLDERS = 2, 4

OPEN_WORDS = {
    "що",
    "чого",
    "чому",
    "чим",
    "навіщо",
    "як",
    "яка",
    "яке",
    "який",
    "які",
    "якого",
    "якої",
    "якому",
    "якій",
    "яким",
    "якими",
    "яких",
    "яку",
    "коли",
    "хто",
    "кого",
    "кому",
    "ким",
    "де",
    "куди",
    "звідки",
    "скільки",
    "наскільки",
    "розкажіть",
    "опишіть",
    "поясніть",
    "наведіть",
    "назвіть",
    "перелічіть",
}
IMPERATIVES = {"розкажіть", "опишіть", "поясніть", "наведіть", "назвіть", "перелічіть"}
PREPOSITIONS = {
    "в",
    "у",
    "на",
    "з",
    "із",
    "зі",
    "до",
    "для",
    "за",
    "від",
    "після",
    "при",
    "про",
    "під",
    "над",
    "через",
    "без",
    "між",
    "серед",
    "по",
    "о",
    "а",
    "і",
    "й",
    "та",
}
WORD = re.compile(r"[\w'’ʼ-]+")


def plural(n: int, one: str, few: str, many: str) -> str:
    """Українська форма слова після числа: 1 питання, 2 питання, 5 питань."""
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} {one}"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} {few}"
    return f"{n} {many}"


def as_text(node_input) -> str:
    """Перше повідомлення графа надходить як types.Content, а не рядок."""
    if hasattr(node_input, "parts"):
        return "".join(p.text or "" for p in node_input.parts or [])
    return str(node_input or "")


def is_open_question(text: str) -> bool:
    """Відкрите питання починається з питального слова, а не з «Чи», і не має «так чи ні»."""
    words = WORD.findall(text.lower())
    while words and words[0] in PREPOSITIONS:
        words = words[1:]
    if not words or words[0] not in OPEN_WORDS:
        return False
    if "так чи ні" in text.lower():
        return False
    return text.rstrip().endswith("?") or words[0] in IMPERATIVES


def question_issues(plan: dict) -> list[str]:
    """Формальні вимоги до набору питань, які перевіряє код, а не модель."""
    issues = []
    stakeholders = [s.strip() for s in plan.get("stakeholders") or []]
    questions = plan.get("questions") or []
    if not MIN_STAKEHOLDERS <= len(stakeholders) <= MAX_STAKEHOLDERS:
        issues.append(
            f"Потрібно {MIN_STAKEHOLDERS}-{MAX_STAKEHOLDERS} стейкхолдери, "
            f"отримано {len(stakeholders)}."
        )
    if not MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS:
        issues.append(
            f"Потрібно {MIN_QUESTIONS}-{MAX_QUESTIONS} питань, "
            f"отримано {len(questions)}."
        )
    ids = [q.get("id") for q in questions]
    if len(set(ids)) != len(ids):
        issues.append("Ідентифікатори питань повторюються.")
    for q in questions:
        if not is_open_question(q.get("text", "")):
            issues.append(f"Питання {q.get('id')} закрите: «{q.get('text', '')}».")
        if q.get("stakeholder", "").strip() not in stakeholders:
            issues.append(
                f"Питання {q.get('id')} адресоване невідомому стейкхолдеру "
                f"«{q.get('stakeholder')}»."
            )
    for s in stakeholders:
        count = sum(q.get("stakeholder", "").strip() == s for q in questions)
        if count < 2:
            issues.append(
                f"Стейкхолдер «{s}» має {plural(count, 'питання', 'питання', 'питань')}, "
                "потрібно щонайменше 2."
            )
    return issues


def conflict_issues(report: dict, answers: dict) -> list[str]:
    """Кожен конфлікт має посилатися на два різні наявні твердження."""
    known = {s.get("id") for s in (answers or {}).get("statements", [])}
    issues = []
    for c in (report or {}).get("conflicts", []):
        a, b = c.get("statement_a"), c.get("statement_b")
        if a == b:
            issues.append(f"Конфлікт {c.get('id')} посилається двічі на {a}.")
        for ref in (a, b):
            if ref not in known:
                issues.append(
                    f"Конфлікт {c.get('id')} посилається на відсутнє твердження {ref}."
                )
    return issues


def intake(ctx: Context, node_input) -> Event:
    """Перевіряє запит користувача і готує стан."""
    text = as_text(node_input).strip()
    ctx.state["drafts"] = 0
    ctx.state["feedback"] = ""
    ctx.state["lead_comments"] = ""
    ctx.state["question_issues"] = []
    ctx.state["conflict_fixes"] = 0
    ctx.state["conflict_feedback"] = ""
    ctx.state["dropped_conflicts"] = []
    if len(text) < MIN_REQUEST_CHARS:
        return Event(
            route="reject",
            output=f"Опишіть проєкт і стейкхолдерів щонайменше в {MIN_REQUEST_CHARS} "
            "символах.",
        )
    if len(text) > MAX_REQUEST_CHARS:
        return Event(
            route="reject",
            output=f"Запит довший за {MAX_REQUEST_CHARS} символів; скоротіть його.",
        )
    ctx.state["request"] = text
    return Event(route="ok", output=text)


def question_check(ctx: Context, node_input) -> Event:
    """Guardrail після дизайнера: закриті питання повертаємо без витрат на інших агентів."""
    ctx.state["drafts"] = ctx.state.get("drafts", 0) + 1
    issues = question_issues(node_input or {})
    if issues and ctx.state["drafts"] < MAX_DRAFTS:
        ctx.state["feedback"] = "Виправ: " + " ".join(issues)
        return Event(route="fix", output=issues)
    ctx.state["question_issues"] = issues  # на останній спробі лише фіксуємо
    ctx.state["conflict_fixes"] = 0
    ctx.state["conflict_feedback"] = ""
    return Event(route="ok", output=node_input)


def conflict_check(ctx: Context, node_input) -> Event:
    """Конфлікт без двох наявних тверджень повертаємо детектору, потім відкидаємо."""
    report = node_input or {}
    issues = conflict_issues(report, ctx.state.get("answers"))
    if issues and ctx.state.get("conflict_fixes", 0) < MAX_CONFLICT_FIXES:
        ctx.state["conflict_fixes"] = ctx.state.get("conflict_fixes", 0) + 1
        ctx.state["conflict_feedback"] = " ".join(issues)
        return Event(route="fix", output=issues)
    valid = [
        c
        for c in report.get("conflicts", [])
        if not conflict_issues({"conflicts": [c]}, ctx.state.get("answers"))
    ]
    ctx.state["conflicts"] = {"conflicts": valid}
    ctx.state["dropped_conflicts"] = issues
    return Event(route="ok", output={"conflicts": valid})


def gate(ctx: Context, node_input) -> Event:
    """Рішення провідного аналітика + ліміт ітерацій -> куди йти далі."""
    verdict = node_input or {}
    if verdict.get("decision") == "APPROVE":
        ctx.state["stop_reason"] = "approved"
        return Event(route="publish", output=verdict)
    if ctx.state.get("drafts", 0) >= MAX_DRAFTS:
        ctx.state["stop_reason"] = "max_drafts"
        return Event(route="publish", output=verdict)
    ctx.state["feedback"] = "; ".join(verdict.get("comments", []))
    ctx.state["lead_comments"] = ctx.state["feedback"]
    return Event(route="revise", output=verdict)


def render_report(state: dict) -> str:
    """Збирає підсумковий сценарій інтерв'ю в Markdown зі стану сесії."""
    plan = state.get("plan") or {}
    statements = (state.get("answers") or {}).get("statements", [])
    by_id = {s.get("id"): s for s in statements}
    by_question = {s.get("question_id"): s for s in statements}
    conflicts = (state.get("conflicts") or {}).get("conflicts", [])
    amb = state.get("ambiguities") or {}
    verdict = state.get("verdict") or {}
    lines = [f"# Сценарій інтерв'ю: {plan.get('topic', 'проєкт')}", ""]
    for s in plan.get("stakeholders", []):
        lines += [f"## {s}", ""]
        for q in plan.get("questions", []):
            if q.get("stakeholder", "").strip() != s.strip():
                continue
            lines.append(f"- **{q['id']}.** {q['text']} _(мета: {q.get('goal', '')})_")
            answer = by_question.get(q["id"])
            if answer:
                lines.append(
                    f"  - очікувана відповідь {answer['id']}: {answer['text']}"
                )
        lines.append("")
    lines += ["## Конфлікти вимог", ""]
    if not conflicts:
        lines.append("- Конфліктів не виявлено.")
    for c in conflicts:
        a, b = by_id.get(c["statement_a"], {}), by_id.get(c["statement_b"], {})
        lines += [
            f"- **{c['id']}** ({c['statement_a']} ↔ {c['statement_b']}): {c['description']}",
            f"  - {a.get('stakeholder', '?')}: «{a.get('text', '')}»",
            f"  - {b.get('stakeholder', '?')}: «{b.get('text', '')}»",
            f"  - уточнити: {c['clarifying_question']}",
        ]
    lines += ["", "## Неоднозначні формулювання", ""]
    lines += [
        f"- {a['statement_id']}: «{a['term']}» → {a['clarifying_question']}"
        for a in amb.get("ambiguities", [])
    ] or ["- Не виявлено."]
    lines += ["", "## Непокриті теми", ""]
    lines += [f"- {t}" for t in amb.get("missing_topics", [])] or ["- Немає."]
    lines += [
        "",
        "## Рішення",
    ]
    if state.get("stop_reason") == "single call":
        lines.append(
            "Один агент, один виклик моделі: рецензування керівником не передбачене."
        )
    else:
        lines.append(
            f"{verdict.get('decision', '?')} після "
            f"{plural(state.get('drafts', 0), 'чернетки', 'чернеток', 'чернеток')} "
            f"(причина зупинки: {state.get('stop_reason', '?')})."
        )
    if verdict.get("decision") != "APPROVE" and verdict.get("comments"):
        lines += [
            "",
            "Невиконані зауваження:",
            *[f"- {c}" for c in verdict["comments"]],
        ]
    if state.get("question_issues"):
        lines += [
            "",
            "Порушення формату питань:",
            *[f"- {i}" for i in state["question_issues"]],
        ]
    if state.get("dropped_conflicts"):
        lines += [
            "",
            "Відкинуті конфлікти:",
            *[f"- {i}" for i in state["dropped_conflicts"]],
        ]
    return "\n".join(lines)


def publish(ctx: Context, node_input) -> Event:
    report = render_report(ctx.state.to_dict())
    ctx.state["report"] = report
    return Event(message=report, output=report)


def reject(ctx: Context, node_input) -> Event:
    return Event(message=f"Запит відхилено: {node_input}", output=None)
