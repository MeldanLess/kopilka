"""Проверка состояния сервиса."""

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.deps import DbSession
from app.schemas import Health

router = APIRouter(tags=["meta"])
settings = get_settings()


@router.get("/health", response_model=Health, summary="Проверка состояния")
def health(db: DbSession) -> Health:
    """Живость и готовность в одном месте.

    Сообщает о базе как "up" или "down", а не падает с ошибкой, чтобы система
    мониторинга могла отличить «процесс жив, но база недоступна» от «процесса
    нет».
    """
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception:
        # Проверка состояния не должна бросать: она обязана сообщить о сломанной
        # базе, а не уронить процесс, который об этом сообщает.
        database = "down"

    return Health(
        status="ok" if database == "up" else "degraded",
        database=database,
        version=settings.version,
    )
