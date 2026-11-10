"""Сводка за месяц: итоги, доли категорий и границы месяца."""

from fastapi.testclient import TestClient

from app.enums import Kind
from app.models import Category


def test_summary_of_empty_month_is_zero(auth_client: TestClient) -> None:
    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["income"] == "0.00"
    assert body["expense"] == "0.00"
    assert body["balance"] == "0.00"
    assert body["by_category"] == []


def test_summary_counts_income_and_expense(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=income_category.id,
        kind=Kind.INCOME,
        amount="1000.00",
        occurred_on="2026-11-05",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="450.50",
        occurred_on="2026-11-06",
    )

    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    body = response.json()
    assert body["income"] == "1000.00"
    assert body["expense"] == "450.50"
    # Остаток — это разница, а не два независимых числа.
    assert body["balance"] == "549.50"


def test_summary_splits_by_category(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=income_category.id,
        kind=Kind.INCOME,
        amount="1000.00",
    )
    make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="300.00"
    )
    make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="100.00"
    )

    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    slices = response.json()["by_category"]
    by_name = {item["name"]: item for item in slices}
    assert set(by_name) == {"Зарплата", "Еда"}
    assert by_name["Еда"]["amount"] == "400.00"
    assert by_name["Еда"]["count"] == 2


def test_summary_shares_are_relative_to_own_kind(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    """Доля расхода считается от расходов, доля дохода — от доходов.

    Смешивать их в один знаменатель бессмысленно: «Еда» не может занимать
    40% доходов только потому, что расходов было больше.
    """
    make_transaction(
        owner_id=user.id,
        category_id=income_category.id,
        kind=Kind.INCOME,
        amount="1000.00",
    )
    make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="400.00"
    )

    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    by_name = {item["name"]: item for item in response.json()["by_category"]}
    assert by_name["Еда"]["share"] == 1.0
    assert by_name["Зарплата"]["share"] == 1.0


def test_summary_shares_split_between_categories(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="300.00"
    )
    second = auth_client.post(
        "/categories", json={"name": "Транспорт", "kind": "expense"}
    ).json()
    make_transaction(
        owner_id=user.id,
        category_id=second["id"],
        amount="100.00",
    )

    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    by_name = {item["name"]: item for item in response.json()["by_category"]}
    assert by_name["Еда"]["share"] == 0.75
    assert by_name["Транспорт"]["share"] == 0.25


def test_summary_ignores_other_months(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="10.00",
        occurred_on="2026-10-31",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="20.00",
        occurred_on="2026-11-01",
    )

    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    assert response.json()["expense"] == "20.00"


def test_summary_of_december_does_not_include_january(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    """Граница года: в декабрь не попадает первое января.

    Это как раз тот случай, где легко ошибиться в арифметике месяцев.
    """
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="31.00",
        occurred_on="2026-12-31",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="01.00",
        occurred_on="2027-01-01",
    )

    december = auth_client.get(
        "/summary/monthly", params={"year": 2026, "month": 12}
    ).json()
    january = auth_client.get(
        "/summary/monthly", params={"year": 2027, "month": 1}
    ).json()

    assert december["expense"] == "31.00"
    assert january["expense"] == "1.00"


def test_summary_rejects_impossible_month(auth_client: TestClient) -> None:
    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 13})

    assert response.status_code == 422


def test_summary_requires_month(auth_client: TestClient) -> None:
    response = auth_client.get("/summary/monthly", params={"year": 2026})

    assert response.status_code == 422


def test_summary_ignores_other_users_transactions(
    auth_client: TestClient, other_user, db_session, make_transaction
) -> None:
    """Чужие деньги не попадают в сводку."""
    category = Category(
        owner_id=other_user.id, name="Еда", kind=Kind.EXPENSE, color="#ef4444"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    make_transaction(owner_id=other_user.id, category_id=category.id, amount="999.00")

    response = auth_client.get("/summary/monthly", params={"year": 2026, "month": 11})

    body = response.json()
    assert body["expense"] == "0.00"
    assert body["by_category"] == []
