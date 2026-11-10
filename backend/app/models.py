"""ORM-модели.

Три таблицы:

* ``users``        — кому разрешено пользоваться API.
* ``categories``   — категории доходов и расходов, у каждого пользователя свои.
* ``transactions`` — сами денежные операции.

Два решения здесь стоят отдельного внимания.

**Деньги — это ``NUMERIC``, а не ``float``.** Двоичная точка не умеет хранить
десятую долю копейки, и ошибка округления в сумме — это ошибка в зарплате.
``NUMERIC(14, 2)`` в PostgreSQL и ``Decimal`` в Python хранят ровно то, что
написано, а сложение не накапливает погрешность.

**Вид операции лежит рядом с суммой, а не выводится из категории.** Иначе любая
сводка по месяцу требует соединения с таблицей категорий, а вид операции всё
равно нужен почти везде. Дублирование данных здесь осознанное: категория задаёт
*вид* операции, а поле ``kind`` у транзакции — это её *собственный* вид, и
согласованность между ними проверяется при записи.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import Kind, enum_values


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    categories: Mapped[list["Category"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Category(Base):
    """Категория доходов или расходов.

    Название уникально в пределах пользователя, а не в пределах базы: у двух
    людей вполне может быть категория «Проезд».
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[Kind] = mapped_column(
        SAEnum(Kind, name="category_kind", values_callable=enum_values), index=True
    )
    #: Цвет для диаграммы — строка в формате ``#RRGGBB``. Хранится текстом,
    #: потому что это оформление, а не часть предметной области.
    color: Mapped[str] = mapped_column(String(7), default="#6b7280")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category"
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_categories_owner_name"),
        Index("ix_categories_owner_kind", "owner_id", "kind"),
    )


class Transaction(Base):
    """Денежная операция: доход или расход."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )

    kind: Mapped[Kind] = mapped_column(
        SAEnum(Kind, name="transaction_kind", values_callable=enum_values), index=True
    )
    #: Точная сумма: ``NUMERIC(14, 2)`` — это 12 целых и 2 копейки, с запасом
    #: на миллионы рублей и отрицательные значения невозможны по определению.
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="transactions")
    category: Mapped[Category] = relationship(back_populates="transactions")

    __table_args__ = (
        # Списки всегда фильтруются по владельцу и сортируются по дате операции.
        Index("ix_transactions_owner_occurred", "owner_id", "occurred_on"),
        Index("ix_transactions_owner_kind_occurred", "owner_id", "kind", "occurred_on"),
    )
