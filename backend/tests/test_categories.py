"""Категории: создание, изменение, удаление и границы."""

from fastapi.testclient import TestClient


def test_list_is_empty_for_new_account(auth_client: TestClient) -> None:
    response = auth_client.get("/categories")

    assert response.status_code == 200
    assert response.json() == []


def test_create_category(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/categories",
        json={"name": "Еда", "kind": "expense", "color": "#ef4444"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Еда"
    assert body["kind"] == "expense"
    assert body["color"] == "#ef4444"


def test_create_category_rejects_duplicate_name(auth_client: TestClient) -> None:
    payload = {"name": "Еда", "kind": "expense"}
    assert auth_client.post("/categories", json=payload).status_code == 201

    response = auth_client.post("/categories", json=payload)

    assert response.status_code == 409
    assert "уже есть" in response.json()["detail"]


def test_create_category_rejects_blank_name(auth_client: TestClient) -> None:
    response = auth_client.post("/categories", json={"name": "   ", "kind": "expense"})

    assert response.status_code == 422


def test_create_category_rejects_bad_color(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/categories", json={"name": "Еда", "kind": "expense", "color": "красный"}
    )

    assert response.status_code == 422


def test_create_category_rejects_unknown_kind(auth_client: TestClient) -> None:
    response = auth_client.post("/categories", json={"name": "Еда", "kind": "перевод"})

    assert response.status_code == 422


def test_list_filters_by_kind(auth_client: TestClient) -> None:
    auth_client.post("/categories", json={"name": "Еда", "kind": "expense"})
    auth_client.post("/categories", json={"name": "Зарплата", "kind": "income"})

    response = auth_client.get("/categories", params={"kind": "income"})

    assert response.status_code == 200
    categories = response.json()
    assert [category["name"] for category in categories] == ["Зарплата"]


def test_patch_category(auth_client: TestClient, expense_category) -> None:
    response = auth_client.patch(
        f"/categories/{expense_category.id}", json={"name": "Продукты"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Продукты"


def test_patch_category_rejects_duplicate_name(
    auth_client: TestClient, expense_category, income_category
) -> None:
    response = auth_client.patch(
        f"/categories/{expense_category.id}", json={"name": "Зарплата"}
    )

    assert response.status_code == 409


def test_patch_category_cannot_change_kind(auth_client: TestClient, expense_category) -> None:
    """Вид категории менять нельзя: он определяет, доходом или расходом была операция."""
    response = auth_client.patch(
        f"/categories/{expense_category.id}", json={"kind": "income"}
    )

    # `extra="forbid"` в схеме изменения отвергает неизвестное поле.
    assert response.status_code == 422


def test_patch_unknown_category_is_404(auth_client: TestClient) -> None:
    response = auth_client.patch(
        "/categories/00000000-0000-0000-0000-000000000000", json={"name": "Еда"}
    )

    assert response.status_code == 404


def test_delete_category(auth_client: TestClient, expense_category) -> None:
    response = auth_client.delete(f"/categories/{expense_category.id}")

    assert response.status_code == 204
    assert auth_client.get("/categories").json() == []


def test_delete_category_with_transactions_is_409(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    """Нельзя удалить категорию, в которой есть операции: иначе суммы за месяц
    посчитаются не полностью."""
    make_transaction(
        owner_id=user.id, category_id=expense_category.id, amount="50.00"
    )

    response = auth_client.delete(f"/categories/{expense_category.id}")

    assert response.status_code == 409
    assert "операции" in response.json()["detail"]


def test_delete_unknown_category_is_404(auth_client: TestClient) -> None:
    response = auth_client.delete("/categories/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
