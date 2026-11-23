"""Готові відповіді агентів для тестів."""

REQUEST = (
    "Онлайн-запис до сімейного лікаря в міській поліклініці. "
    "Стейкхолдери: пацієнт, лікар, адміністратор реєстратури."
)

DESIGNER = "requirements interview designer"
SIMULATOR = "simulate the stakeholders"
CONFLICTS = "requirements conflict detector"
AMBIGUITY = "requirements ambiguity analyst"
LEAD = "lead business analyst"

PLAN = {
    "topic": "Онлайн-запис до лікаря",
    "stakeholders": ["пацієнт", "лікар"],
    "questions": [
        {
            "id": "Q1",
            "stakeholder": "пацієнт",
            "text": "Як ви зараз записуєтеся до лікаря?",
            "goal": "поточний процес",
        },
        {
            "id": "Q2",
            "stakeholder": "пацієнт",
            "text": "За скільки днів наперед ви хочете бачити вільні слоти?",
            "goal": "горизонт запису",
        },
        {
            "id": "Q3",
            "stakeholder": "пацієнт",
            "text": "Розкажіть, що буває, коли ви запізнюєтеся.",
            "goal": "правила запізнень",
        },
        {
            "id": "Q4",
            "stakeholder": "лікар",
            "text": "Скільки хвилин триває типовий прийом?",
            "goal": "тривалість слоту",
        },
        {
            "id": "Q5",
            "stakeholder": "лікар",
            "text": "За скільки днів наперед ви готові відкривати розклад?",
            "goal": "горизонт запису",
        },
        {
            "id": "Q6",
            "stakeholder": "лікар",
            "text": "Що має відбуватися, коли пацієнт не прийшов?",
            "goal": "неявки",
        },
    ],
}
ANSWERS = {
    "statements": [
        {
            "id": "S1",
            "stakeholder": "пацієнт",
            "question_id": "Q1",
            "text": "Телефоную в реєстратуру.",
        },
        {
            "id": "S2",
            "stakeholder": "пацієнт",
            "question_id": "Q2",
            "text": "Хочу бачити слоти на місяць уперед.",
        },
        {
            "id": "S3",
            "stakeholder": "пацієнт",
            "question_id": "Q3",
            "text": "Мене переносять, це незручно.",
        },
        {
            "id": "S4",
            "stakeholder": "лікар",
            "question_id": "Q4",
            "text": "Прийом триває 15 хвилин.",
        },
        {
            "id": "S5",
            "stakeholder": "лікар",
            "question_id": "Q5",
            "text": "Розклад відомий лише на тиждень.",
        },
        {
            "id": "S6",
            "stakeholder": "лікар",
            "question_id": "Q6",
            "text": "Слот має швидко звільнятися.",
        },
    ]
}
CONFLICT_REPORT = {
    "conflicts": [
        {
            "id": "C1",
            "statement_a": "S2",
            "statement_b": "S5",
            "description": "Пацієнт хоче запис на місяць, лікар відкриває розклад на тиждень.",
            "clarifying_question": "Який горизонт запису влаштує обидві сторони?",
        },
    ]
}
BAD_CONFLICTS = {
    "conflicts": [
        {
            "id": "C1",
            "statement_a": "S2",
            "statement_b": "S99",
            "description": "Посилання на неіснуюче твердження.",
            "clarifying_question": "Що саме суперечить?",
        },
    ]
}
AMBIGUITIES = {
    "ambiguities": [
        {
            "statement_id": "S6",
            "term": "швидко",
            "clarifying_question": "Через скільки хвилин після неявки слот має звільнятися?",
        }
    ],
    "missing_topics": ["скасування запису"],
}
APPROVE = {"decision": "APPROVE", "comments": []}
REVISE = {"decision": "REVISE", "comments": ["додай питання про скасування запису"]}


def script(designer=None, conflicts=None, lead=None) -> dict:
    """Сценарій усіх агентів; списки відповідей можна замінити."""
    return {
        DESIGNER: designer or [PLAN],
        SIMULATOR: [ANSWERS],
        CONFLICTS: conflicts or [CONFLICT_REPORT],
        AMBIGUITY: [AMBIGUITIES],
        LEAD: lead or [APPROVE],
    }
