"""Регистрация, вход и «кто я»."""

from fastapi.testclient import TestClient


def test_register_creates_account(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "Новый Пользователь",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["full_name"] == "Новый Пользователь"
    # Пароль не должен попадать в ответ — ни в открытом виде, ни в виде хеша.
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_creates_default_categories(client: TestClient) -> None:
    """Вместе с аккаунтом появляются категории по умолчанию."""
    client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )

    response = client.post(
        "/auth/token", data={"username": "new@example.com", "password": "password123"}
    )
    token = response.json()["access_token"]

    categories = client.get(
        "/categories", headers={"Authorization": f"Bearer {token}"}
    ).json()

    names = {category["name"] for category in categories}
    assert {"Зарплата", "Еда"} <= names


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {"email": "user@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 201

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Пользователь с такой почтой уже есть"


def test_register_is_case_insensitive(client: TestClient) -> None:
    client.post(
        "/auth/register", json={"email": "user@example.com", "password": "password123"}
    )

    response = client.post(
        "/auth/register", json={"email": "USER@example.com", "password": "password123"}
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"email": "user@example.com", "password": "short"}
    )

    assert response.status_code == 422


def test_register_rejects_malformed_email(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"email": "не-почта", "password": "password123"}
    )

    assert response.status_code == 422


def test_login_returns_token_and_user(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    response = client.post(
        "/auth/token", data={"username": "user@example.com", "password": "password123"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "user@example.com"
    assert body["access_token"]


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    response = client.post(
        "/auth/token", data={"username": "user@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверная почта или пароль"


def test_login_does_not_reveal_whether_email_exists(client: TestClient) -> None:
    """Ответ на «нет такого пользователя» и на «неверный пароль» одинаковый."""
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    unknown = client.post(
        "/auth/token", data={"username": "nobody@example.com", "password": "password123"}
    )
    wrong = client.post(
        "/auth/token", data={"username": "user@example.com", "password": "wrong-password"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer nonsense"})

    assert response.status_code == 401


def test_me_returns_current_user(auth_client: TestClient, user) -> None:
    response = auth_client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == user.email
