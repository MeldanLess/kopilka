"""Схемы Pydantic — форма каждого запроса и ответа.

Это публичный контракт API. ORM-модели остаются внутренними: переименование
колонки не должно молча менять JSON, на который полагаются клиенты.

**Деньги в JSON — это строки.** ``Decimal`` Pydantic сериализует в JSON как
строку (``"1234.56"``), и это не формальность: если бы сумма превратилась в
число IEEE 754, клиент сложил бы её и получил ``1234.5599999999999``. Сумма
приходит строкой — разбирает её клиент тем языком, в котором у него нет
двоичной точки.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.config import get_settings
from app.enums import Kind
from app.security import MAX_PASSWORD_BYTES

settings = get_settings()

#: Денежная сумма: не больше 12 целых и ровно 2 знака после запятой.
Money = Decimal

#: Ограничения вынесены в `Annotated`, а не в `Field(...)` рядом с `| None`.
#:
#: Поведение ограничений на необязательном поле (`Optional[str] = Field(max_length=…)`)
#: зависит от версии Pydantic, и на это не стоит опираться. Через `Annotated`
#: ограничение гарантированно применяется к самой строке, а `None` остаётся
#: отдельной, разрешённой ветвью.
FullName = Annotated[str, Field(max_length=120)]
CategoryName = Annotated[str, Field(min_length=1, max_length=80)]
CategoryColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
TransactionNote = Annotated[str, Field(max_length=500)]
Amount = Annotated[
    Decimal,
    Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
        description="Сумма всегда положительная: знак задаёт вид операции.",
    ),
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Пользователи и аутентификация
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=settings.password_min_length,
        max_length=MAX_PASSWORD_BYTES,
        description="Пароль в открытом виде; хранится только bcrypt-хеш.",
    )
    full_name: FullName | None = None

    @field_validator("password")
    @classmethod
    def _password_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("password must not be blank")
        return value


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenWithUser(Token):
    user: UserRead


# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: Kind
    color: str = Field(
        default="#6b7280",
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Цвет в формате #RRGGBB — используется в диаграмме.",
    )

    @field_validator("name")
    @classmethod
    def _name_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()


class CategoryUpdate(BaseModel):
    """Все поля необязательные — PATCH меняет только то, что прислали."""

    model_config = ConfigDict(extra="forbid")

    name: CategoryName | None = None
    color: CategoryColor | None = None

    @field_validator("name")
    @classmethod
    def _name_is_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()


class CategoryRead(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    kind: Kind
    color: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Операции
# ---------------------------------------------------------------------------


class TransactionBase(BaseModel):
    category_id: uuid.UUID
    kind: Kind
    amount: Amount
    occurred_on: date
    note: TransactionNote | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    """Все поля необязательные — PATCH меняет только то, что прислали."""

    model_config = ConfigDict(extra="forbid")

    category_id: uuid.UUID | None = None
    kind: Kind | None = None
    amount: Amount | None = None
    occurred_on: date | None = None
    note: TransactionNote | None = None


class TransactionRead(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    category_id: uuid.UUID
    kind: Kind
    amount: Money
    occurred_on: date
    note: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Постраничный вывод и сводка
# ---------------------------------------------------------------------------


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


class CategorySlice(BaseModel):
    """Сколько денег ушло в одну категорию за месяц."""

    category_id: uuid.UUID
    name: str
    color: str
    amount: Money
    count: int
    share: float = Field(
        description="Доля категории в сумме своего вида операций (0-1)."
    )


class MonthlySummary(BaseModel):
    """Сводка за месяц: сколько пришло, сколько ушло и куда."""

    year: int
    month: int
    income: Money
    expense: Money
    balance: Money
    by_category: list[CategorySlice]


class Health(BaseModel):
    status: str
    database: str
    version: str
