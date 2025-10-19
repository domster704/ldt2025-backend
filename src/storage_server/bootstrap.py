from typing import Any

import structlog
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from storage_server.infrastructure.routes import ROUTERS
from storage_server.logger import setup_logger
from storage_server.middlewares import HTTPLogMiddleware
from storage_server.di_container import sync_container, async_container
from storage_server.settings import HTTPServerSettings, AppSettings


def create_server(http_server_settings: HTTPServerSettings, app_settings: AppSettings) -> FastAPI:
    app = FastAPI(
        title="storage-server",
        root_path="/api",
        version=http_server_settings.api_version,
        docs_url=None if not app_settings.is_dev() else "/docs",
        redoc_url=None,
    )

    app.add_middleware(
        HTTPLogMiddleware,
        logger=structlog.get_logger('http'),
        dev=app_settings.is_dev()
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=http_server_settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        if router[1] is None:
            app.include_router(router[0])
        else:
            app.include_router(router[0], prefix=router[1])

    return app


def bootstrap() -> tuple[FastAPI, dict[str, Any]]:
    http_server_settings = sync_container.get_id()
    app_settings = sync_container.get_id()
    app = create_server(http_server_settings, app_settings)
    setup_dishka(async_container, app)
    setup_logger(app_settings.is_dev())

    return app, {
        'host': http_server_settings.host,
        'port': http_server_settings.port,
        'run_mode': app_settings.run_mode,
    }