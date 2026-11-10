"""Сводка за месяц: сколько пришло, сколько ушло и куда."""

from fastapi import APIRouter, Query

from app.crud import monthly_summary
from app.deps import CurrentUser, DbSession
from app.schemas import MonthlySummary

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get(
    "/monthly", response_model=MonthlySummary, summary="Сводка за месяц"
)
def read_monthly_summary(
    current_user: CurrentUser,
    db: DbSession,
    year: int = Query(ge=2000, le=2100, description="Год."),
    month: int = Query(ge=1, le=12, description="Месяц, 1-12."),
) -> MonthlySummary:
    """Собрать сводку за месяц.

    Ответ содержит три вещи, которых не даёт ни одна таблица операций сама по
    себе: сколько пришло, сколько ушло, остаток; а также разрез по категориям
    с долей каждой в сумме своего вида операций.
    """
    return monthly_summary(db, owner_id=current_user.id, year=year, month=month)
