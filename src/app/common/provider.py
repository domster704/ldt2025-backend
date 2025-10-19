import os
from collections.abc import Container, Iterable, AsyncIterable
from os import PathLike
from typing import Literal, Annotated

from dishka import Provider, Scope, provide, make_container, make_async_container, AsyncContainer, FromComponent
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession

from app.common.settings import AppSettings, HTTPServerSettings
from app.modules.core.infra.gateways.llm import HttpxLLMGateway, MockLLMGateway
from app.modules.core.infra.gateways.patient import HttpxPatientGateway
from app.modules.core.infra.repositories.ctg import SQLAlchemyCTGRepository
from app.modules.core.infra.repositories.patient import SQLAlchemyPatientRepository
from app.modules.core.settings import DatabaseSettings
from app.modules.core.usecases.ports.ctg_repository import CTGRepository
from app.modules.core.usecases.ports.llm_gateway import LLMGateway
from app.modules.core.usecases.ports.patient_gateway import PatientGateway
from app.modules.core.usecases.ports.patient_repository import PatientRepository

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

    @provide
    def app_settings(self) -> AppSettings:
        return AppSettings(_env_file=self._env_file)

    @provide
    def http_server_settings(self) -> HTTPServerSettings:
        return HTTPServerSettings(_env_file=self._env_file)


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

    @provide(scope=Scope.REQUEST, provides=PatientRepository)
    async def patient_repo(self, session: AsyncSession) -> SQLAlchemyPatientRepository:
        return SQLAlchemyPatientRepository(session)

    @provide(scope=Scope.REQUEST, provides=CTGRepository)
    async def ctg_repo(self, session: AsyncSession) -> CTGRepository:
        return SQLAlchemyCTGRepository(session)


class LLMGetawayProvider(Provider):
    component = 'llm'

    @provide(scope=Scope.APP)
    async def httpx_client(
            self, app_settings: Annotated[AppSettings, FromComponent('')]
    ) -> AsyncIterable[AsyncClient]:
        async with AsyncClient(base_url=str(app_settings.llm_uri)) as client:
            yield client

    @provide(scope=Scope.REQUEST, provides=LLMGateway)
    async def llm_gateway(self, httpx_client: AsyncClient) -> MockLLMGateway:
        return MockLLMGateway(httpx_client)


class ExternalServerProvider(Provider):
    component = 'external_server'

    @provide(scope=Scope.APP)
    async def httpx_client(
            self, app_settings: Annotated[AppSettings, FromComponent('')]
    ) -> AsyncIterable[AsyncClient]:
        async with AsyncClient(base_url=str(app_settings.external_server_uri)) as client:
            yield client

    @provide(scope=Scope.REQUEST, provides=PatientGateway)
    async def patient_gateway(self, httpx_client: AsyncClient) -> HttpxPatientGateway:
        return HttpxPatientGateway(httpx_client)


_sync_container: Container | None = None
_async_container: Container | None = None

def create_di_container() -> None:
    global _sync_container, _async_container
    if _sync_container is None:
        _sync_container = make_container(SettingsProvider(env_file=_ENV_PATH), DatabaseProvider())
    if _async_container is None:
        _async_container = make_async_container(
            SettingsProvider(env_file=_ENV_PATH),
            DatabaseProvider(),
            LLMGetawayProvider(),
            ExternalServerProvider(),
        )

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