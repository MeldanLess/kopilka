"""Выгрузка в CSV: файл должен открываться в русском Excel без плясок."""

import codecs

from fastapi.testclient import TestClient

from app.enums import Kind
from app.models import Category

#: Метка порядка байтов, которой начинается CSV.
BOM = codecs.BOM_UTF8.decode("utf-8")


def _rows(response) -> list[list[str]]:
    """Разобрать тело ответа на строки и колонки."""
    text = response.text
    assert text.startswith(BOM), "Файл должен начинаться с BOM, иначе Excel примет его за CP1251"
    lines = text.lstrip(BOM).splitlines()
    return [line.split(";") for line in lines]


def test_export_returns_csv_file(auth_client: TestClient) -> None:
    response = auth_client.get("/export/transactions.csv")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('"kopilka-all.csv"')


def test_export_has_russian_headers(auth_client: TestClient) -> None:
    response = auth_client.get("/export/transactions.csv")

    rows = _rows(response)
    assert rows[0] == ["Дата", "Вид", "Категория", "Сумма", "Заметка"]


def test_export_formats_amount_with_comma(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    """Десятичная запятая — как в русской локали Excel."""
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="1234.56",
        occurred_on="2026-11-10",
        note="Обед",
    )

    response = auth_client.get("/export/transactions.csv")

    rows = _rows(response)
    assert rows[1] == ["2026-11-10", "Расход", "Еда", "1234,56", "Обед"]


def test_export_labels_income_and_expense(
    auth_client: TestClient, expense_category, income_category, user, make_transaction
) -> None:
    make_transaction(
        owner_id=user.id,
        category_id=income_category.id,
        kind=Kind.INCOME,
        amount="1000.00",
        occurred_on="2026-11-10",
    )
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="10.00",
        occurred_on="2026-11-11",
    )

    response = auth_client.get("/export/transactions.csv")

    rows = _rows(response)
    kinds = {row[1] for row in rows[1:]}
    assert kinds == {"Доход", "Расход"}


def test_export_escapes_formula_in_note(
    auth_client: TestClient, expense_category, user, make_transaction
) -> None:
    """Заметка, начинающаяся с `=`, не должна стать формулой в Excel."""
    make_transaction(
        owner_id=user.id,
        category_id=expense_category.id,
        amount="10.00",
        occurred_on="2026-11-11",
        note="=1+1",
    )

    response = auth_client.get("/export/transactions.csv")

    rows = _rows(response)
    assert rows[1][4] == "'=1+1"


def test_export_respects_date_range(
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
        "/export/transactions.csv",
        params={"date_from": "2026-11-01", "date_to": "2026-11-30"},
    )

    rows = _rows(response)
    assert len(rows) == 2
    assert rows[1][0] == "2026-11-15"
    assert "kopilka-2026-11-01-2026-11-30.csv" in response.headers["content-disposition"]


def test_export_of_empty_account_is_only_header(auth_client: TestClient) -> None:
    response = auth_client.get("/export/transactions.csv")

    rows = _rows(response)
    assert len(rows) == 1


def test_export_ignores_other_users_transactions(
    auth_client: TestClient, other_user, db_session, make_transaction
) -> None:
    category = Category(
        owner_id=other_user.id, name="Еда", kind=Kind.EXPENSE, color="#ef4444"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    make_transaction(owner_id=other_user.id, category_id=category.id, amount="999.00")

    response = auth_client.get("/export/transactions.csv")

    rows = _rows(response)
    assert len(rows) == 1
