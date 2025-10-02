import os
from collections.abc import Container, Iterable, AsyncIterable
from os import PathLike
from typing import Literal

from dishka import Provider, Scope, provide, make_container, make_async_container, AsyncContainer
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession

from app.modules.core.infra.adapters.ctg import CTGRepository
from app.modules.core.infra.adapters.patient import PatientRepository
from app.modules.core.settings import DatabaseSettings
from app.modules.core.usecases.ports.ctg import CTGPort
from app.modules.core.usecases.ports.patients import PatientPort

_ENV_PATH = os.environ.get("ENV_PATH", None)

class SettingsProvider(Provider):
    """Провайдер уровня приложения."""

    scope = Scope.APP

    def __init__(self, env_file: PathLike | None):
        super().__init__()
        self._env_file = str(env_file) if env_file is not None else env_file

    @provide
    def db_settings(self) -> DatabaseSettings:
        return DatabaseSettings(_env_file=self._env_file)


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    def engine(self, settings: DatabaseSettings) -> Iterable[AsyncEngine]:
        engine = create_async_engine(settings.db_url, pool_pre_ping=True)
        yield engine

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker:
        return async_sessionmaker(bind=engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(self, session_factory: async_sessionmaker) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST, provides=PatientPort)
    async def patient_repo(self, session: AsyncSession) -> PatientRepository:
        return PatientRepository(session)

    @provide(scope=Scope.REQUEST, provides=CTGPort)
    async def ctg_repo(self, session: AsyncSession) -> CTGPort:
        return CTGRepository(session)


_sync_container: Container | None = None
_async_container: Container | None = None

def create_di_container() -> None:
    global _sync_container, _async_container
    if _sync_container is None:
        _sync_container = make_container(SettingsProvider(env_file=_ENV_PATH), DatabaseProvider())
    if _async_container is None:
        _async_container = make_async_container(SettingsProvider(env_file=_ENV_PATH), DatabaseProvider())

def get_container(di_type: Literal['sync', 'async']) -> Container | AsyncContainer:
    match di_type:
        case 'sync':
            if _sync_container is None:
                raise RuntimeError("Sync DI container not initialized")
            return _sync_container
        case 'async':
            if _async_container is None:
                raise RuntimeError("Async DI container not initialized")
            return _async_container
        case _:
            raise RuntimeError("Unknown DI type")