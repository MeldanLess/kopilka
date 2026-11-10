"""Денежные операции: доходы и расходы."""

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.crud import (
    KindMismatch,
    NotFound,
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)
from app.deps import CurrentUser, DbSession
from app.enums import Kind
from app.schemas import Page, TransactionCreate, TransactionRead, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=Page[TransactionRead], summary="Список операций")
def read_transactions(
    current_user: CurrentUser,
    db: DbSession,
    kind: Kind | None = Query(default=None, description="Только доходы или расходы."),
    category_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None, description="Дата операции, с."),
    date_to: date | None = Query(default=None, description="Дата операции, по."),
    search: str | None = Query(default=None, description="Поиск по заметке."),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[TransactionRead]:
    """Вернуть операции текущего пользователя.

    Список отсортирован по дате операции (от новых к старым) — так он выглядит
    как лента, а не как простыня, и так же он отображается в интерфейсе.
    """
    rows, total = list_transactions(
        db,
        owner_id=current_user.id,
        kind=kind,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    return Page[TransactionRead](
        items=[TransactionRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Записать операцию",
)
def post_transaction(
    payload: TransactionCreate, current_user: CurrentUser, db: DbSession
) -> TransactionRead:
    """Записать доход или расход.

    Категория обязана принадлежать тому же пользователю и иметь тот же вид
    операции. Категория расходов не может оказаться у дохода — это 409, а не
    404: категория существует, несовместима она.
    """
    try:
        transaction = create_transaction(
            db, owner_id=current_user.id, payload=payload
        )
    except NotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except KindMismatch as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    return TransactionRead.model_validate(transaction)


@router.get(
    "/{transaction_id}", response_model=TransactionRead, summary="Одна операция"
)
def read_transaction(
    transaction_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> TransactionRead:
    """Вернуть одну операцию."""
    try:
        transaction = get_transaction(
            db, owner_id=current_user.id, transaction_id=transaction_id
        )
    except NotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    return TransactionRead.model_validate(transaction)


@router.patch(
    "/{transaction_id}", response_model=TransactionRead, summary="Изменить операцию"
)
def patch_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> TransactionRead:
    """Изменить операцию.

    Правило «вид операции совпадает с видом категории» проверяется и здесь:
    смена категории на категорию другого вида без смены вида операции —
    это 409.
    """
    try:
        transaction = get_transaction(
            db, owner_id=current_user.id, transaction_id=transaction_id
        )
        transaction = update_transaction(
            db, transaction=transaction, payload=payload
        )
    except NotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except KindMismatch as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    return TransactionRead.model_validate(transaction)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить операцию",
)
def remove_transaction(
    transaction_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    """Удалить операцию."""
    try:
        transaction = get_transaction(
            db, owner_id=current_user.id, transaction_id=transaction_id
        )
    except NotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    delete_transaction(db, transaction=transaction)
