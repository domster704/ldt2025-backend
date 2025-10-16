import os

from dishka import Provider, Scope, provide, make_container, make_async_container
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from .settings import DatabaseSettings, AppSettings, HTTPServerSettings

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
    def http_server_settings(self) -> HTTPServerSettings:
        return HTTPServerSettings(_env_file=self._env_file)


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    def engine(self, settings: DatabaseSettings) -> AsyncEngine:
        engine = create_async_engine(settings.db_url, pool_pre_ping=True)
        yield engine

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker:
        return async_sessionmaker(bind=engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(self, session_factory: async_sessionmaker) -> AsyncSession:
        async with session_factory() as session:
            yield session


sync_container = make_container(SettingsProvider(_ENV_PATH), DatabaseProvider())
async_container = make_async_container(DatabaseProvider())