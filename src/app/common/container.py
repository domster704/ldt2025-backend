from __future__ import annotations

from collections.abc import Iterable, AsyncIterable
from pathlib import Path

from dishka import Provider, Scope, provide, make_async_container, AsyncContainer
from dishka.integrations.fastapi import FastapiProvider
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.common.settings import DatabaseSettings
from app.modules.monitoring.health.aggregation import HealthCheck

ENV_DIR = Path(__file__).resolve().parents[3] / 'run' / '.envs'


class SettingsProvider(Provider):
    """Провайдер уровня приложения."""

    scope = Scope.APP

    def __init__(self, env_file: str | Path):
        super().__init__()
        self._env_file = str(env_file)
        self._engine: AsyncEngine | None = None

    @provide
    def db_settings(self) -> DatabaseSettings:
        return DatabaseSettings(_env_file=self._env_file)


class DbProvider(Provider):
    @provide(scope=Scope.APP)
    def engine(self, settings: DatabaseSettings) -> Iterable[AsyncEngine]:
        engine = create_async_engine(settings.db_url, pool_pre_ping=True)
        try:
            yield engine
        finally:
            engine.dispose()

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker:
        return async_sessionmaker(bind=engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(self, session_factory: async_sessionmaker) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            yield session


class HealthProvider(Provider):
    scope = Scope.APP

    @provide
    def health_checks(
        self,
        db_engine: AsyncEngine,
    ) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        return checks


def build_container(env_path: str) -> AsyncContainer:
    provider = SettingsProvider(env_path)
    return make_async_container(provider, FastapiProvider())
