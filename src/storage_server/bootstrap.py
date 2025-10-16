import structlog
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .infrastructure.routes import ROUTERS
from .logger import setup_logger
from .middlewares import HTTPLogMiddleware
from .di_container import sync_container
from .settings import HTTPServerSettings, AppSettings


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


def bootstrap() -> FastAPI:
    http_server_settings = sync_container(HTTPServerSettings)
    app_settings = sync_container(AppSettings)
    app = create_server(http_server_settings, app_settings)
    setup_logger(app_settings.is_dev())

    return app