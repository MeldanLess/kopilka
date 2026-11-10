# Бэкенд «Копилки»

FastAPI-сервис личного финансового трекера: аккаунты, категории, денежные
операции, сводка по месяцу и выгрузка в CSV.

Описание проекта, список решений и разбор trade-off — в [README.md](../README.md)
в корне репозитория.

## Что внутри

| Путь | Что это |
|---|---|
| `app/main.py` | Точка входа: middleware, обработчики ошибок, подключение роутеров |
| `app/routers/` | HTTP-слой: только разбор запроса и вызов слоя данных |
| `app/crud.py` | Слой доступа к данным: весь SQL живёт здесь |
| `app/models.py` | ORM-модели: `users`, `categories`, `transactions` |
| `app/schemas.py` | Схемы Pydantic — публичный контракт API |
| `alembic/versions/` | Миграции: история схемы, а не снимок текущей |
| `tests/` | Набор тестов против настоящего PostgreSQL |

## Запуск локально

```bash
cp .env.example .env
docker compose up --build
```

Дальше:

* API — <http://localhost:8000>, документация — <http://localhost:8000/docs>
* Проверка состояния — <http://localhost:8000/health>

## Тесты

Тестам нужен настоящий PostgreSQL: SQLite не умеет ни колонки UUID, ни
нативные типы enum, ни `NUMERIC` для денег.

```bash
docker compose up -d db
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
```

Набор тестов сам создаёт базу `kopilka_test`, накатывает на неё миграции
Alembic и очищает её между тестами.

## Демо-данные

```bash
python -m app.seed
```

Появятся демо-аккаунт `demo@example.com` (пароль `demo12345`) и операции за
последние три месяца — их достаточно, чтобы сводка и диаграмма выглядели
живыми.
