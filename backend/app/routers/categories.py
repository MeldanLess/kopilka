"""Категории доходов и расходов."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.crud import (
    CategoryInUse,
    DuplicateCategory,
    NotFound,
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)
from app.deps import CurrentUser, DbSession
from app.enums import Kind
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead], summary="Список категорий")
def read_categories(
    current_user: CurrentUser,
    db: DbSession,
    kind: Kind | None = Query(default=None, description="Только доходы или расходы."),
) -> list[CategoryRead]:
    """Вернуть категории текущего пользователя.

    Категории других пользователей не видны никогда: выборка идёт по
    владельцу, а не по всему списку с последующей фильтрацией.
    """
    return [
        CategoryRead.model_validate(category)
        for category in list_categories(db, owner_id=current_user.id, kind=kind)
    ]


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать категорию",
)
def post_category(
    payload: CategoryCreate, current_user: CurrentUser, db: DbSession
) -> CategoryRead:
    """Создать категорию.

    Название уникально в пределах пользователя: две категории «Еда» у одного
    человека — это опечатка, а не две разные категории.
    """
    try:
        category = create_category(db, owner_id=current_user.id, payload=payload)
    except DuplicateCategory as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    return CategoryRead.model_validate(category)


@router.patch(
    "/{category_id}", response_model=CategoryRead, summary="Изменить категорию"
)
def patch_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> CategoryRead:
    """Изменить название или цвет категории.

    Вид категории (`kind`) менять нельзя: он задаёт, доходом или расходом была
    операция, и смена вида сломала бы уже записанные операции. Поэтому в схеме
    изменения поля `kind` нет вовсе — нельзя даже случайно.
    """
    try:
        category = get_category(
            db, owner_id=current_user.id, category_id=category_id
        )
    except NotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error

    try:
        category = update_category(db, category=category, payload=payload)
    except DuplicateCategory as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    return CategoryRead.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
)
def remove_category(
    category_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    """Удалить категорию.

    Категорию, в которой есть операции, удалить нельзя: иначе операции
    остались бы без смысла, а суммы за месяц — посчитаны не полностью.
    """
    try:
        category = get_category(
            db, owner_id=current_user.id, category_id=category_id
        )
    except NotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error

    try:
        delete_category(db, category=category)
    except CategoryInUse as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
