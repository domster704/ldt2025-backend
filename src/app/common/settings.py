from enum import Enum
from functools import cached_property

from pydantic import HttpUrl
from pydantic_settings import SettingsConfigDict, BaseSettings

class InitializationError(Exception):
    pass

class RunMode(Enum):
    PROD = 'prod'
    TEST = 'test'
    DEV = 'dev'

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8', extra='ignore')

    run_mode: RunMode = 'dev'
    emulator_uri: HttpUrl

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

app_settings = AppSettings()
http_server_settings = HTTPServerSettings()
