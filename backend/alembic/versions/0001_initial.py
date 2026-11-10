"""Начальная схема

Создаёт два типа enum в PostgreSQL, а также таблицы users, categories и
transactions.

Идентификатор ревизии: 0001_initial
Предыдущая ревизия:
Дата создания: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


KIND_VALUES = ("income", "expense")


def upgrade() -> None:
    bind = op.get_bind()

    # Типы enum создаём явно, а колонки потом ссылаются на них с
    # create_type=False. Если дать SQLAlchemy создать их на месте, вторая
    # таблица с тем же типом упадёт с ошибкой.
    postgresql.ENUM(*KIND_VALUES, name="category_kind").create(bind, checkfirst=True)
    postgresql.ENUM(*KIND_VALUES, name="transaction_kind").create(bind, checkfirst=True)

    kind_enum = postgresql.ENUM(*KIND_VALUES, name="category_kind", create_type=False)
    transaction_kind_enum = postgresql.ENUM(
        *KIND_VALUES, name="transaction_kind", create_type=False
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("kind", kind_enum, nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name", name="uq_categories_owner_name"),
    )
    op.create_index("ix_categories_owner_id", "categories", ["owner_id"])
    op.create_index("ix_categories_kind", "categories", ["kind"])
    op.create_index(
        "ix_categories_owner_kind", "categories", ["owner_id", "kind"]
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", transaction_kind_enum, nullable=False),
        # NUMERIC, а не FLOAT: сумма в деньгах обязана храниться ровно.
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        # RESTRICT, а не CASCADE: удаление категории с операциями должно
        # требовать явного решения, а не молча забирать историю денег.
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_owner_id", "transactions", ["owner_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_kind", "transactions", ["kind"])
    op.create_index("ix_transactions_occurred_on", "transactions", ["occurred_on"])
    op.create_index(
        "ix_transactions_owner_occurred",
        "transactions",
        ["owner_id", "occurred_on"],
    )
    op.create_index(
        "ix_transactions_owner_kind_occurred",
        "transactions",
        ["owner_id", "kind", "occurred_on"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transactions_owner_kind_occurred", table_name="transactions"
    )
    op.drop_index("ix_transactions_owner_occurred", table_name="transactions")
    op.drop_index("ix_transactions_occurred_on", table_name="transactions")
    op.drop_index("ix_transactions_kind", table_name="transactions")
    op.drop_index("ix_transactions_category_id", table_name="transactions")
    op.drop_index("ix_transactions_owner_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_categories_owner_kind", table_name="categories")
    op.drop_index("ix_categories_kind", table_name="categories")
    op.drop_index("ix_categories_owner_id", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    postgresql.ENUM(name="transaction_kind").drop(bind, checkfirst=True)
    postgresql.ENUM(name="category_kind").drop(bind, checkfirst=True)
