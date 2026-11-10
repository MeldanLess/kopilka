"""Операции: запись, чтение, изменение, фильтры и доменные правила."""

from fastapi.testclient import TestClient

from app.enums import Kind


def test_create_transaction(auth_client: TestClient, expense_category) -> None:
    response = auth_client.post(
        "/transactions",
        json={
            "category_id": str(expense_category.id),
            "kind": "expense",
            "amount": "450.50",
            "occurred_on": "2026-11-10",
            "note": "Обед",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "expense"
    assert body["note"] == "Обед"
    # Сумма приходит строкой: так в JSON не появляется двоичная точка.
    assert body["amount"] == "450.50"


def test_create_transaction_rejects_category_of_other_kind(
    auth_client: TestClient, expense_category
) -> None:
    """Категория расходов не может оказаться у дохода."""
    response = auth_client.post(
        "/transactions",
        json={
            "category_id": str(expense_category.id),
            "kind": "income",
            "amount": "450.50",
            "occurred_on": "2026-11-10",
        },
    )

    assert response.status_code == 409
    assert "не может быть" in response.json()["detail"]


def test_create_transaction_rejects_unknown_category(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/transactions",
        json={
            "category_id": "00000000-0000-0000-0000-000000000000",
            "kind": "expense",
            "amount": "10.00",
            "occurred_on": "2026-11-10",
        },
    )

    assert response.status_code == 404


def test_create_transaction_rejects_non_positive_amount(
    auth_client: TestClient, expense_category
) -> None:
    """Сумма всегда положительная: знак задаёт вид операции."""
    response = auth_client.post(
        "/transactions",
        json={
            "category_id": str(expense_category.id),
            "kind": "expense",
            "amount": "0",
            "occurred_on": "2026-11-10",
        },
    )

    assert response.status_code == 422


def test_create_transaction_rejects_too_many_decimals(
    auth_client: TestClient, expense_category
) -> None:
    response = auth_client.post(
        "/transactions",
        json={
            "category_id": str(expense_category.id),
            "kind": "expense",
            "amount": "10.555",
            "occurred_on": "2026-11-10",
        },
    )

    assert response.status_code == 422


def test_create_transaction_rejects_malformed_date(
    auth_client: TestClient, expense_category
) -> None:
    response = auth_client.post(
        "/transactions",
        json={
            "category_id": str(expense_category.id),
            "kind": "expense",
            "amount": "10.00",
            "occurred_on": "10.11.2026",
        },
    )

    assert response.status_code == 422


def test_list_transactions_is_paginated(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    for index in range(5):
        make_transaction(
            owner_id=user.id,
            category_id=expense_category.id,
            amount="10.00",
            occurred_on=f"2026-11-0{index + 1}",
        )

    response = auth_client.get("/transactions", params={"limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 0


def test_list_transactions_is_sorted_by_date_desc(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="10.00",
        occurred_on="2026-11-01",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="20.00",
        occurred_on="2026-11-20",
    )

    response = auth_client.get("/transactions")

    dates = [item["occurred_on"] for item in response.json()["items"]]
    assert dates == ["2026-11-20", "2026-11-01"]


def test_list_transactions_filters_by_kind(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        kind=Kind.EXPENSE,
        amount="10.00",
    )
    make_transaction(
        owner_id=user.id,
        category_id=income_category.id,
        kind=Kind.INCOME,
        amount="1000.00",
    )

    response = auth_client.get("/transactions", params={"kind": "income"})

    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["kind"] == "income"


def test_list_transactions_filters_by_date_range(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="10.00",
        occurred_on="2026-10-15",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="20.00",
        occurred_on="2026-11-15",
    )

    response = auth_client.get(
        "/transactions",
        params={"date_from": "2026-11-01", "date_to": "2026-11-30"},
    )

    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["occurred_on"] == "2026-11-15"


def test_list_transactions_filters_by_category(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="10.00"
    )
    make_transaction(
        owner_id=user.id,
        category_id=income_category.id,
        kind=Kind.INCOME,
        amount="20.00",
    )

    response = auth_client.get(
        "/transactions", params={"category_id": str(income_category.id)}
    )

    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["category_id"] == str(income_category.id)


def test_list_transactions_searches_in_note(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="10.00",
        note="Кофе",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="20.00",
        note="Обед",
    )

    response = auth_client.get("/transactions", params={"search": "кофе"})

    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["note"] == "Кофе"


def test_get_transaction(auth_client: TestClient, expense_category, user, make_transaction) -> None:
    transaction = make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="77.77"
    )

    response = auth_client.get(f"/transactions/{transaction.id}")

    assert response.status_code == 200
    assert response.json()["amount"] == "77.77"


def test_get_unknown_transaction_is_404(auth_client: TestClient) -> None:
    response = auth_client.get("/transactions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_patch_transaction(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    transaction = make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="10.00"
    )

    response = auth_client.patch(
        f"/transactions/{transaction.id}", json={"amount": "25.50"}
    )

    assert response.status_code == 200
    assert response.json()["amount"] == "25.50"


def test_patch_transaction_rejects_kind_mismatch(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    """Смена вида операции без смены категории — конфликт."""
    transaction = make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="10.00"
    )

    response = auth_client.patch(
        f"/transactions/{transaction.id}", json={"kind": "income"}
    )

    assert response.status_code == 409


def test_patch_transaction_rejects_unknown_field(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    transaction = make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="10.00"
    )

    response = auth_client.patch(
        f"/transactions/{transaction.id}", json={"owner_id": "00000000-0000-0000-0000-000000000000"}
    )

    assert response.status_code == 422


def test_delete_transaction(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    transaction = make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="10.00"
    )

    response = auth_client.delete(f"/transactions/{transaction.id}")

    assert response.status_code == 204
    assert auth_client.get("/transactions").json()["total"] == 0
