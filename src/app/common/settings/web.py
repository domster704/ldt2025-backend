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

class AppSettings(BaseSettings):
    run_mode: RunMode = 'dev'


app_settings = AppSettings()


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

# class WebsocketsSettings(BaseSettings):
#     model_config = SettingsConfigDict(env_file_encoding='utf-8', extra='ignore')
#
#     HTTP_HOST: str = "0.0.0.0"
#     HTTP_PORT: int = 8001
#     API_VERSION: str
#
#     @cached_property
#     def origins(self):
#         match self.RUN_MODE:
#             case RunMode.PROD:
#                 return ['*']
#             case RunMode.TEST:
#                 return ['*']
#             case RunMode.DEV:
#                 return ['*']
#             case _:
#                 raise InitializationError(f'Unsupported RUN_MODE: {self.RUN_MODE}')

http_server_settings = HTTPServerSettings()
# websocket_settings = WebsocketsSettings()