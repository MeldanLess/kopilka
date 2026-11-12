"""Выгрузка операций в CSV.

Файл сделан так, чтобы его можно было открыть в русском Excel двойным
щелчком и сразу увидеть нормальный текст:

* разделитель ``;`` — в русской локали Excel это разделитель списка;
* десятичная запятая — тоже как в русской локали;
* ``BOM`` в начале файла — без него Excel считает файл в кодировке CP1251 и
  кириллица превращается в мусор.

Имя файла содержит период, поэтому выгрузки не перетирают друг друга.
"""

import codecs
import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Query, Response

from app.crud import list_transactions
from app.deps import CurrentUser, DbSession
from app.enums import Kind
from app.models import Transaction

router = APIRouter(prefix="/export", tags=["export"])

#: Заголовки колонок — по-русски, потому что файл открывают в Excel, а не в
#: программе, которая знает английский интерфейс.
HEADERS = ["Дата", "Вид", "Категория", "Сумма", "Заметка"]

#: Метка порядка байтов в начале файла. Excel по умолчанию читает CSV как
#: CP1251, и без неё кириллица в категориях превращается в мусор.
#:
#: Символ берётся из `codecs`, а не пишется невидимым знаком прямо в коде:
#: невидимый знак легко потерять при копировании, и файл перестанет
#: открываться в Excel по-человечески.
BOM = codecs.BOM_UTF8.decode("utf-8")

KIND_LABELS = {Kind.INCOME: "Доход", Kind.EXPENSE: "Расход"}

#: Знаки, с которых Excel и LibreOffice считают ячейку формулой.
#:
#: Категория или заметка может начинаться с ``=``, ``+``, ``-``, ``@`` — и
#: тогда при открытии файла таблица выполнит это как формулу. В худшем случае
#: пользователь сам себе запускает макрос из чужой вкладки. Знак апострофа
#: перед текстом превращает ячейку в обычный текст: Excel показывает его при
#: редактировании, но не выполняет.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: str) -> str:
    """Экранирует значение, которое таблица приняла бы за формулу."""
    if value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def _period_label(date_from: date | None, date_to: date | None) -> str:
    """Подпись периода для имени файла — только латиница и цифры.

    Имя файла попадает в заголовок `Content-Disposition`, а заголовки HTTP
    кодируются в latin-1: кириллица там превратилась бы в ошибку 500.
    """
    if date_from is not None and date_to is not None:
        return f"{date_from.isoformat()}-{date_to.isoformat()}"
    if date_from is not None:
        return f"from-{date_from.isoformat()}"
    if date_to is not None:
        return f"until-{date_to.isoformat()}"
    return "all"


def _format_amount(value) -> str:
    """Сумма с запятой в качестве десятичного разделителя."""
    return f"{value:.2f}".replace(".", ",")


def _build_csv(transactions: list[Transaction], categories: dict[uuid.UUID, str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADERS)
    for transaction in transactions:
        writer.writerow(
            [
                transaction.occurred_on.isoformat(),
                KIND_LABELS[transaction.kind],
                _safe_cell(categories.get(transaction.category_id, "")),
                _format_amount(transaction.amount),
                _safe_cell(transaction.note or ""),
            ]
        )
    return buffer.getvalue()


@router.get("/transactions.csv", summary="Выгрузить операции в CSV")
def export_transactions(
    current_user: CurrentUser,
    db: DbSession,
    date_from: date | None = Query(default=None, description="Дата операции, с."),
    date_to: date | None = Query(default=None, description="Дата операции, по."),
) -> Response:
    """Выгрузить операции пользователя в CSV-файл.

    Выгружаются все операции за период, без постраничного ограничения: файл
    предназначен для просмотра целиком, а не для отрисовки в списке.
    """
    transactions, _ = list_transactions(
        db,
        owner_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        limit=10_000,
        offset=0,
    )

    categories = {
        transaction.category_id: transaction.category.name
        for transaction in transactions
        if transaction.category is not None
    }

    # BOM идёт первым байтом файла: без него Excel считает файл в CP1251 и
    # кириллица в названиях категорий превращается в мусор.
    body = BOM + _build_csv(transactions, categories)

    # Имя файла — только латиница: заголовки HTTP кодируются в latin-1, и
    # кириллица в имени файла превратила бы ответ в 500.
    filename = f"kopilka-{_period_label(date_from, date_to)}.csv"

    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
