"""Слой доступа к данным.

Весь SQL живёт здесь, поэтому роутеры занимаются только HTTP, а тесты могут
проверять доменные правила, не выходя в сеть.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.enums import Kind
from app.models import Category, Transaction, User
from app.schemas import (
    CategoryCreate,
    CategorySlice,
    CategoryUpdate,
    MonthlySummary,
    TransactionCreate,
    TransactionUpdate,
)


class NotFound(Exception):
    """Бросается, когда строки нет или она принадлежит не тому, кто спросил."""


class KindMismatch(Exception):
    """Вид операции не совпадает с видом её категории."""

    def __init__(self, category_kind: Kind, transaction_kind: Kind):
        self.category_kind = category_kind
        self.transaction_kind = transaction_kind
        super().__init__(
            f"Категория «{category_kind.value}» не может быть у операции "
            f"«{transaction_kind.value}»"
        )


class CategoryInUse(Exception):
    """Категория не пуста: её удаление сломало бы ссылки в операциях."""


class DuplicateCategory(Exception):
    """У пользователя уже есть категория с таким именем."""


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    ).scalar_one_or_none()


def create_user(
    db: Session, *, email: str, hashed_password: str, full_name: str | None
) -> User:
    user = User(email=email.lower(), hashed_password=hashed_password, full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------


def list_categories(
    db: Session, *, owner_id: uuid.UUID, kind: Kind | None = None
) -> list[Category]:
    statement: Select = select(Category).where(Category.owner_id == owner_id)
    if kind is not None:
        statement = statement.where(Category.kind == kind)
    return list(
        db.execute(statement.order_by(Category.kind, Category.name)).scalars().all()
    )


def get_category(
    db: Session, *, owner_id: uuid.UUID, category_id: uuid.UUID
) -> Category:
    category = db.get(Category, category_id)
    # 404, а не 403, для чужой категории: 403 подтверждал бы, что такой id
    # существует.
    if category is None or category.owner_id != owner_id:
        raise NotFound("Категория не найдена")
    return category


def create_category(
    db: Session, *, owner_id: uuid.UUID, payload: CategoryCreate
) -> Category:
    existing = db.execute(
        select(Category).where(
            Category.owner_id == owner_id,
            func.lower(Category.name) == payload.name.lower(),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateCategory("Категория с таким названием уже есть")

    category = Category(owner_id=owner_id, **payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, *, category: Category, payload: CategoryUpdate
) -> Category:
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        clash = db.execute(
            select(Category).where(
                Category.owner_id == category.owner_id,
                func.lower(Category.name) == changes["name"].lower(),
                Category.id != category.id,
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise DuplicateCategory("Категория с таким названием уже есть")

    for field, value in changes.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, *, category: Category) -> None:
    used = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.category_id == category.id)
    ).scalar_one()
    if used:
        # Категория с операциями удаляется только вместе с ними, а это отдельное
        # осознанное действие — молча терять историю денег нельзя.
        raise CategoryInUse("Нельзя удалить категорию, в которой есть операции")

    db.delete(category)
    db.commit()


#: Категории, которые создаются вместе с аккаунтом.
#:
#: Пустой трекер бесполезен: чтобы записать первую операцию, нужно сначала
#: придумать категорию, а человеку, который только начал считать деньги, это
#: лишнее решение на пустом месте. Набор небольшой и его легко изменить.
DEFAULT_CATEGORIES: tuple[tuple[str, Kind, str], ...] = (
    ("Зарплата", Kind.INCOME, "#22c55e"),
    ("Подработка", Kind.INCOME, "#84cc16"),
    ("Подарок", Kind.INCOME, "#eab308"),
    ("Еда", Kind.EXPENSE, "#ef4444"),
    ("Транспорт", Kind.EXPENSE, "#f97316"),
    ("Жильё", Kind.EXPENSE, "#8b5cf6"),
    ("Здоровье", Kind.EXPENSE, "#06b6d4"),
    ("Развлечения", Kind.EXPENSE, "#ec4899"),
    ("Прочее", Kind.EXPENSE, "#6b7280"),
)


def create_default_categories(db: Session, *, owner_id: uuid.UUID) -> list[Category]:
    """Создаёт набор категорий по умолчанию для нового пользователя."""
    categories = [
        Category(owner_id=owner_id, name=name, kind=kind, color=color)
        for name, kind, color in DEFAULT_CATEGORIES
    ]
    db.add_all(categories)
    db.commit()
    return categories


# ---------------------------------------------------------------------------
# Операции
# ---------------------------------------------------------------------------


def create_transaction(
    db: Session, *, owner_id: uuid.UUID, payload: TransactionCreate
) -> Transaction:
    category = get_category(db, owner_id=owner_id, category_id=payload.category_id)
    if category.kind != payload.kind:
        raise KindMismatch(category.kind, payload.kind)

    transaction = Transaction(owner_id=owner_id, **payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction(
    db: Session, *, owner_id: uuid.UUID, transaction_id: uuid.UUID
) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None or transaction.owner_id != owner_id:
        raise NotFound("Операция не найдена")
    return transaction


def list_transactions(
    db: Session,
    *,
    owner_id: uuid.UUID,
    kind: Kind | None = None,
    category_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    statement: Select = select(Transaction).where(Transaction.owner_id == owner_id)

    if kind is not None:
        statement = statement.where(Transaction.kind == kind)
    if category_id is not None:
        statement = statement.where(Transaction.category_id == category_id)
    if date_from is not None:
        statement = statement.where(Transaction.occurred_on >= date_from)
    if date_to is not None:
        statement = statement.where(Transaction.occurred_on <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(Transaction.note.ilike(pattern))

    total = db.execute(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ).scalar_one()

    rows = db.execute(
        statement.order_by(Transaction.occurred_on.desc(), Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return list(rows), total


def update_transaction(
    db: Session, *, transaction: Transaction, payload: TransactionUpdate
) -> Transaction:
    changes = payload.model_dump(exclude_unset=True)

    # Правило «вид операции совпадает с видом категории» проверяется и при
    # изменении: смена категории без смены вида — как раз тот случай, когда
    # операция незаметно превращается в доход.
    new_category_id = changes.get("category_id")
    category = transaction.category
    if new_category_id is not None:
        category = get_category(
            db, owner_id=transaction.owner_id, category_id=new_category_id
        )

    new_kind = changes.get("kind", transaction.kind)
    if category.kind != new_kind:
        raise KindMismatch(category.kind, new_kind)

    for field, value in changes.items():
        setattr(transaction, field, value)
    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(db: Session, *, transaction: Transaction) -> None:
    db.delete(transaction)
    db.commit()


# ---------------------------------------------------------------------------
# Сводка
# ---------------------------------------------------------------------------


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """Первый день месяца и первый день следующего.

    Верхняя граница не включивается, поэтому запрос не ломается на последнем
    дне месяца и не зависит от того, как именно хранится время операции.
    """
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def monthly_summary(
    db: Session, *, owner_id: uuid.UUID, year: int, month: int
) -> MonthlySummary:
    """Собирает сводку за месяц.

    Считается в SQL одной группировкой: операции одного человека за месяц — это
    сотни строк, и база делает это быстрее и надёжнее, чем Python.
    """
    start, end = _month_bounds(year, month)

    rows = db.execute(
        select(
            Transaction.kind.label("kind"),
            Category.id.label("category_id"),
            Category.name.label("name"),
            Category.color.label("color"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.owner_id == owner_id,
            Transaction.occurred_on >= start,
            Transaction.occurred_on < end,
        )
        .group_by(Transaction.kind, Category.id, Category.name, Category.color)
        .order_by(Category.name)
    ).all()

    income = Decimal("0.00")
    expense = Decimal("0.00")
    # Сначала считаем итоги, потом доли: доля — это отношение к сумме своего
    # вида операций, а сумма известна только после того, как сложены все куски.
    grouped: list[tuple[Kind, uuid.UUID, str, str, Decimal, int]] = []

    for row in rows:
        total = row.total if row.total is not None else Decimal("0.00")
        if row.kind == Kind.INCOME:
            income += total
        else:
            expense += total
        grouped.append(
            (row.kind, row.category_id, row.name, row.color, total, row.count)
        )

    slices: list[CategorySlice] = []
    for kind, category_id, name, color, total, count in grouped:
        # Доля считается от суммы своего вида операций: доля расхода «Еды» в
        # расходах и доля дохода «Зарплаты» в доходах — разные знаменатели, и
        # смешивать их в одну цифру бессмысленно.
        base = income if kind == Kind.INCOME else expense
        slices.append(
            CategorySlice(
                category_id=category_id,
                name=name,
                color=color,
                amount=total,
                count=count,
                share=round(float(total / base), 4) if base else 0.0,
            )
        )

    return MonthlySummary(
        year=year,
        month=month,
        income=income,
        expense=expense,
        balance=income - expense,
        by_category=slices,
    )
