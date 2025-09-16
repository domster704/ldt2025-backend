from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator, Annotated, TypeVar, Type

from fastapi import Depends, params

from db.repository.repository import BaseRepository, UnitOfWork
from db.repository.user_repository import UserRepository
from settings import Settings

T = TypeVar("T", bound=BaseRepository)


async def UoW_dep() -> AsyncGenerator[UnitOfWork, None]:
    async with UnitOfWork() as uow:
        yield uow


def _repo_dep(repo_cls: Type[T]) -> params.Depends:
    """Возвращает зависимость FastAPI для любого репозитория.

    Args:
        repo_cls: Класс репозитория, принимающий UnitOfWork (uow=...) в конструкторе.

    Returns:
        Функцию-зависимость, которую можно передать в Depends().
    """

    def _factory(
            uow: Annotated[UnitOfWork, Depends(UoW_dep)]
    ) -> T:
        repo = repo_cls(uow=uow)
        try:
            yield repo
        finally:
            pass

    return Depends(_factory)


# ==============================
# Репозитории
# ==============================

UserRepositoryDepends = _repo_dep(UserRepository)


@lru_cache
def get_settings() -> Settings:
    return Settings()
