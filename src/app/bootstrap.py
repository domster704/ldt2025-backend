from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from .common.container import build_container
from .common.settings.web import RunMode, app_settings, http_server_settings
from .logger import setup_logger
from .middlewares import HTTPLogMiddleware

from .modules.core.infra.routes.http.base import router as core_router
from .modules.monitoring.health.router import router as health_router
from .modules.ingest.infra.routes.base import router as ingest_router

ROUTERS: list[tuple[APIRouter, str | None]] = [
    (health_router, None),
    (core_router, None),
    (ingest_router, "/ws/ingest")
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await app.state.dishka_container.close()


def _is_dev() -> bool:
    return app_settings.run_mode == RunMode.DEV

def create_server() -> FastAPI:
    app = FastAPI(
        title="woym-market-server",
        root_path="/backend",
        version=http_server_settings.api_version,
        docs_url=None if not _is_dev() else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )


    app.add_middleware(
        HTTPLogMiddleware,
        logger=structlog.get_logger('http'),
        dev=_is_dev()
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


def create_app(env_name: str = ".env") -> FastAPI:
    container = build_container(env_name)

    app = create_server()

    setup_dishka(container, app)
    setup_logger(_is_dev())

    return app