"""Наполнение базы демо-данными.

Запуск:  python -m app.seed

Данные правдоподобны и осмысленно распределены по месяцам, чтобы сводка за
месяц выглядела как настоящая: зарплата приходит в начале месяца, а расходы
растянуты по всем дням.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import create_default_categories, create_user, get_user_by_email
from app.database import SessionLocal
from app.enums import Kind
from app.models import Category, Transaction
from app.security import hash_password

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"

#: Расходы по категориям: диапазон суммы в рублях за одну операцию.
EXPENSES: dict[str, tuple[int, int]] = {
    "Еда": (150, 900),
    "Транспорт": (60, 450),
    "Жильё": (8000, 8000),
    "Здоровье": (300, 2500),
    "Развлечения": (300, 2000),
    "Прочее": (100, 1500),
}

#: Доходы по категориям.
INCOMES: dict[str, tuple[int, int]] = {
    "Зарплата": (95000, 95000),
    "Подработка": (5000, 25000),
    "Подарок": (500, 3000),
}


def _random_amount(rng: random.Random, bounds: tuple[int, int]) -> Decimal:
    low, high = bounds
    # Суммы округляются до копеек: в настоящей жизни суммы вида «1234,56 рубля»
    # встречаются, а «1234,5678 рубля» — нет.
    return Decimal(rng.randint(low * 100, high * 100)) / Decimal(100)


def _month_start(today: date, offset: int) -> date:
    """Первый день месяца, отстоящего от `today` на `offset` месяцев назад.

    Считается через номер месяца, а не вычитанием дней: вычитание 31 дня от
    первого числа прыгает через месяц в месяцах короче 31 дня, и данные
    разъезжаются по датам.
    """
    index = today.year * 12 + (today.month - 1) - offset
    return date(index // 12, index % 12 + 1, 1)


def seed(db: Session, *, months: int = 3) -> tuple[str, int]:
    """Заполняет базу демо-данными. Возвращает почту и число операций."""
    rng = random.Random(20261110)

    user = get_user_by_email(db, DEMO_EMAIL)
    if user is None:
        user = create_user(
            db,
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Демо Пользователь",
        )
        create_default_categories(db, owner_id=user.id)

    categories = list(
        db.execute(select(Category).where(Category.owner_id == user.id)).scalars().all()
    )
    by_name = {category.name: category for category in categories}

    today = date.today()

    created = 0
    for offset in range(months):
        month_start = _month_start(today, offset)
        # Число дней в месяце — это разница между первым днём этого месяца и
        # первым днём следующего. `day=28` плюс четыре дня — самый короткий
        # способ узнать последний день месяца, не заглядывая в календарь.
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        days_in_month = (next_month - month_start).days

        for name, bounds in INCOMES.items():
            category = by_name.get(name)
            if category is None:
                continue
            count = 1 if name == "Зарплата" else rng.randint(0, 2)
            for _ in range(count):
                day = rng.randint(1, min(10, days_in_month))
                db.add(
                    Transaction(
                        owner_id=user.id,
                        category_id=category.id,
                        kind=Kind.INCOME,
                        amount=_random_amount(rng, bounds),
                        occurred_on=month_start + timedelta(days=day - 1),
                        note=None,
                    )
                )
                created += 1

        for name, bounds in EXPENSES.items():
            category = by_name.get(name)
            if category is None:
                continue
            count = 1 if name == "Жильё" else rng.randint(3, 9)
            for _ in range(count):
                day = rng.randint(1, days_in_month)
                occurred_on = month_start + timedelta(days=day - 1)
                if occurred_on > today:
                    continue
                db.add(
                    Transaction(
                        owner_id=user.id,
                        category_id=category.id,
                        kind=Kind.EXPENSE,
                        amount=_random_amount(rng, bounds),
                        occurred_on=occurred_on,
                        note=None,
                    )
                )
                created += 1

    db.commit()
    return DEMO_EMAIL, created


def main() -> None:
    with SessionLocal() as db:
        email, count = seed(db)
    print(f"Готово: {count} операций для {email} (пароль {DEMO_PASSWORD})")


if __name__ == "__main__":
    main()
