import os
from collections.abc import AsyncIterable, Iterable

from dishka import Provider, Scope, provide, make_container, make_async_container
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from storage_server.application.ports.ctg_history_repo import CTGHistoryRepository
from storage_server.application.ports.ctg_result_repo import CTGResultRepository
from storage_server.application.ports.patient_repo import PatientRepository
from storage_server.infrastructure.repositories.ctg_history import SQLAlchemyCTGHistoryRepository
from storage_server.infrastructure.repositories.ctg_result import SQLAlchemyCTGResultRepository
from storage_server.infrastructure.repositories.patient import SQLAlchemyPatientRepository
from storage_server.settings import DatabaseSettings, AppSettings, HTTPServerSettings

_ENV_PATH = os.environ.get("ENV_PATH", None)


class SettingsProvider(Provider):
    """Провайдер уровня приложения."""

    scope = Scope.APP

    def __init__(self, env_file: str | None):
        super().__init__()
        self._env_file = env_file

    @provide
    def db_settings(self) -> DatabaseSettings:
        return DatabaseSettings(_env_file=self._env_file)

    @provide
    def app_settings(self) -> AppSettings:
        return AppSettings(_env_file=self._env_file)

    @provide
    def http_server_settings(self, app_settings: AppSettings) -> HTTPServerSettings:
        return HTTPServerSettings(_env_file=self._env_file, run_mode=app_settings.run_mode)


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

    @provide(scope=Scope.REQUEST)
    async def get_patient_repository(self, session: AsyncSession) -> PatientRepository:
        return SQLAlchemyPatientRepository(
            session=session,
        )

    @provide(scope=Scope.REQUEST)
    async def get_ctg_history_repository(self, session: AsyncSession) -> CTGHistoryRepository:
        return SQLAlchemyCTGHistoryRepository(
            session=session,
        )

    @provide(scope=Scope.REQUEST)
    async def get_ctg_result_repository(self, session: AsyncSession) -> CTGResultRepository:
        return SQLAlchemyCTGResultRepository(session)


sync_container = make_container(SettingsProvider(_ENV_PATH), DatabaseProvider())
async_container = make_async_container(SettingsProvider(_ENV_PATH), DatabaseProvider())