# lab03-mas — мультиагентна система на Google ADK 2.x

ЛР 3 з дисципліни «Штучний інтелект у програмній інженерії», варіант 16 «Підготовка інтерв'ю з вимог».
Виконав: Худокормов Ілля Владиславович, ПЗПІ-23-1.

- `interview-team/` — ADK-проєкт: граф Workflow (`app/agent.py`), схеми (`app/schemas.py`), агенти (`app/agents.py`),
  детерміновані вузли (`app/nodes.py`), базова лінія (`app/baseline.py`), координатор (`app/coordinator.py`),
  запуск і трасування (`run_cli.py`), експеримент (`eval/`), тести з підмінною моделлю (`tests/unit/`)
- `report/` — звіт і паспорт системи MAS-CARD

```
cd interview-team
agents-cli install
echo 'GEMINI_API_KEY="..."' > .env
uv run pytest tests/unit                      # 25 тестів без звернень до API
uv run python run_cli.py "Онлайн-запис до сімейного лікаря. Стейкхолдери: пацієнт, лікар, адміністратор."
uv run python -m eval.show_trace              # трасування останнього запуску
uv run python -m eval.run_experiment          # команда проти одного агента
uv run python -m eval.compare_coordinator     # координатор з експертами
agents-cli playground                         # http://localhost:8080
```
