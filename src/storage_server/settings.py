from enum import Enum
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.settings import app_settings

class InitializationError(Exception):
    pass

class RunMode(Enum):
    PROD = 'prod'
    TEST = 'test'
    DEV = 'dev'

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8', extra='ignore')

    run_mode: RunMode = 'dev'

    def is_dev(self) -> bool:
        return self.run_mode == RunMode.DEV

class HTTPServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8', extra='ignore')

    http_host: str = "0.0.0.0"
    http_port: int = 8000
    api_version: str

    @cached_property
    def origins(self):
        match app_settings.run_mode:
            case RunMode.PROD:
                return ['*']
            case RunMode.TEST:
                return ['*']
            case RunMode.DEV:
                return ['*']
            case _:
                raise InitializationError(f'Unsupported RUN_MODE: {self.RUN_MODE}')

class DatabaseSettings(BaseSettings):
    driver: str
    database_name: str
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None

    @cached_property
    def db_url(self) -> str:
        if self.driver.startswith("sqlite"):
            return f"{self.driver}:///{self.database_name}"

        return (
            f"{self.driver}://{self.username}:{self.password}"
            f"@{self.host}{f':{self.port}' if self.port else ''}"
            f"/{self.database_name}"
        )

    model_config = SettingsConfigDict(env_prefix='DB_', extra='allow')
