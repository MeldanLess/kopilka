"""Проверка состояния сервиса и его самодокументируемость."""

from fastapi.testclient import TestClient


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert body["version"]


def test_health_needs_no_token(client: TestClient) -> None:
    """Проверку состояния вызывает мониторинг, у которого нет учётных данных."""
    assert client.get("/health").status_code == 200


def test_index_points_to_documentation(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_openapi_documents_all_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/auth/register",
        "/auth/token",
        "/auth/me",
        "/categories",
        "/transactions",
        "/summary/monthly",
        "/export/transactions.csv",
        "/health",
    ):
        assert path in paths, f"Эндпоинт {path} не попал в схему OpenAPI"


def test_openapi_has_ru_descriptions(client: TestClient) -> None:
    """Схема API — тоже публичный текст, и он на русском."""
    response = client.get("/openapi.json")

    schema = response.json()
    assert schema["info"]["title"] == "Kopilka API"
    assert "описание" in schema["info"]["description"] or "трекер" in schema["info"]["description"]
