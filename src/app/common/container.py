from __future__ import annotations
from pathlib import Path

from dishka import Provider, Scope, provide, make_async_container, AsyncContainer
from dishka.integrations.fastapi import FastapiProvider
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.common.db import create_db_resources
from app.common.settings import KeycloakSettings, DBSettings
from app.modules.auth.adapters.user_repository_sqlalchemy import SAUserRepository
from app.modules.auth.health import make_auth_checks
from app.modules.monitoring.health.aggregation import HealthCheck

ENV_DIR = Path(__file__).resolve().parents[3] / 'run' / '.envs'


class AppProvider(Provider):
    """Провайдер уровня приложения."""

    scope = Scope.APP

    def __init__(self, env_file: str | Path):
        super().__init__()
        self._env_file = str(env_file)
        self._engine: AsyncEngine | None = None

    @provide
    def db_settings(self) -> DBSettings:
        return DBSettings(_env_file=self._env_file)

    @provide
    def db_engine(self, dbs: DBSettings) -> AsyncEngine:
        resources = create_db_resources(dbs.db_url, echo=dbs.echo)
        self._engine = resources.engine
        return resources.engine

    @provide
    def session_factory(self, db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(bind=db_engine, expire_on_commit=False, class_=AsyncSession)

    @provide
    def user_repo(self, session_factory: async_sessionmaker[AsyncSession]) -> SAUserRepository:
        return SAUserRepository(session_factory)

    @provide
    def health_checks(
        self,
        db_engine: AsyncEngine,
    ) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        checks += make_auth_checks(db_engine)
        return checks


def build_container(env_name: str = ".env") -> AsyncContainer:
    env_path = ENV_DIR / env_name
    provider = AppProvider(env_path)
    return make_async_container(provider, FastapiProvider())
