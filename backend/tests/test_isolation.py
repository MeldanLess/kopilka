"""Изоляция данных: у каждого пользователя свои операции и категории.

Чужие данные должны выглядеть как отсутствующие, а не как запрещённые: ответ
«403» подтвердил бы, что такой идентификатор существует.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.enums import Kind
from app.models import Category


def _category_for(db_session: Session, owner_id, name: str, kind: Kind) -> Category:
    """Создать категорию для произвольного владельца."""
    category = Category(owner_id=owner_id, name=name, kind=kind, color="#ef4444")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def test_other_users_transactions_are_not_listed(
    auth_client: TestClient, other_user, db_session, make_transaction
) -> None:
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)
    make_transaction(owner_id=other_user.id, category_id=category.id, amount="500.00")

    response = auth_client.get("/transactions")

    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_other_users_transaction_is_not_readable(
    auth_client: TestClient, other_user, db_session, make_transaction
) -> None:
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)
    transaction = make_transaction(
        owner_id=other_user.id, category_id=category.id, amount="500.00"
    )

    response = auth_client.get(f"/transactions/{transaction.id}")

    assert response.status_code == 404


def test_other_users_transaction_cannot_be_changed(
    auth_client: TestClient, other_user, db_session, make_transaction
) -> None:
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)
    transaction = make_transaction(
        owner_id=other_user.id, category_id=category.id, amount="500.00"
    )

    response = auth_client.patch(
        f"/transactions/{transaction.id}", json={"amount": "1.00"}
    )

    assert response.status_code == 404


def test_other_users_transaction_cannot_be_deleted(
    auth_client: TestClient, other_user, db_session, make_transaction
) -> None:
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)
    transaction = make_transaction(
        owner_id=other_user.id, category_id=category.id, amount="500.00"
    )

    response = auth_client.delete(f"/transactions/{transaction.id}")

    assert response.status_code == 404


def test_other_users_categories_are_not_listed(
    auth_client: TestClient, other_user, db_session
) -> None:
    _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)

    response = auth_client.get("/categories")

    assert response.json() == []


def test_other_users_category_cannot_be_changed(
    auth_client: TestClient, other_user, db_session
) -> None:
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)

    response = auth_client.patch(f"/categories/{category.id}", json={"name": "Моё"})

    assert response.status_code == 404


def test_other_users_category_cannot_be_deleted(
    auth_client: TestClient, other_user, db_session
) -> None:
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)

    response = auth_client.delete(f"/categories/{category.id}")

    assert response.status_code == 404


def test_cannot_use_other_users_category(
    auth_client: TestClient, other_user, db_session
) -> None:
    """Чужая категория — как несуществующая: 404, а не 403."""
    category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)

    response = auth_client.post(
        "/transactions",
        json={
            "category_id": str(category.id),
            "kind": "expense",
            "amount": "10.00",
            "occurred_on": "2026-11-10",
        },
    )

    assert response.status_code == 404


def test_category_names_do_not_clash_between_users(
    auth_client: TestClient, other_user, db_session
) -> None:
    """Одинаковое название у двух людей — не конфликт."""
    _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)

    response = auth_client.post("/categories", json={"name": "Еда", "kind": "expense"})

    assert response.status_code == 201, response.text


def test_users_see_only_their_own_transactions(
    client: TestClient, auth_client: TestClient, other_token: str, user, other_user,
    db_session, make_transaction
) -> None:
    """Список у каждого свой: у одного — одна операция, у другого — другая."""
    own_category = _category_for(db_session, user.id, "Еда", Kind.EXPENSE)
    other_category = _category_for(db_session, other_user.id, "Еда", Kind.EXPENSE)
    make_transaction(owner_id=user.id, category_id=own_category.id, amount="100.00")
    make_transaction(owner_id=other_user.id, category_id=other_category.id, amount="200.00")

    mine = auth_client.get("/transactions").json()
    theirs = client.get(
        "/transactions", headers={"Authorization": f"Bearer {other_token}"}
    ).json()

    assert mine["total"] == 1
    assert mine["items"][0]["amount"] == "100.00"
    assert theirs["total"] == 1
    assert theirs["items"][0]["amount"] == "200.00"
