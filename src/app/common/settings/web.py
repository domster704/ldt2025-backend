from enum import Enum
from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.exceptions import InitializationError

ROOT_DIR = Path(__file__).resolve().parents[4]
ENV_DIR = ROOT_DIR / 'run' / '.envs'


class RunMode(Enum):
    PROD = 'prod'
    TEST = 'test'
    DEV = 'dev'


class WebServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8', extra='ignore')

    HTTP_HOST: str = "0.0.0.0"
    HTTP_PORT: int = 8000
    RUN_MODE: RunMode = RunMode.DEV
    API_VERSION: str = '2.0.1'

    @cached_property
    def origins(self):
        match self.RUN_MODE:
            case RunMode.PROD:
                return ['https://woym-market.ru']
            case RunMode.TEST:
                return ['https://test.woym-market.ru']
            case RunMode.DEV:
                return ['*']
            case _:
                raise InitializationError(f'Unsupported RUN_MODE: {self.RUN_MODE}')

web_settings = WebServerSettings()