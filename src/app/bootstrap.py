from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from .common.settings import app_settings, RunMode, http_server_settings
from .logger import setup_logger
from .middlewares import HTTPLogMiddleware

from app.modules.core.infra.routes.base import router as core_router
from .modules.core.infra.provider import create_di_container, get_container
from .modules.ingest.infra.routes.base import router as ingest_router
from .modules.streaming.presentation.router.streaming_router import streaming_router


ROUTERS: list[tuple[APIRouter, str | None]] = [
    (core_router, "/http/crud"),
    (ingest_router, "/ws/ingest"),
    (streaming_router, "/ws/streaming"),
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


def create_app() -> FastAPI:
    create_di_container()
    container = get_container('async')
    app = create_server()
    setup_dishka(container, app)
    setup_logger(_is_dev())

    return app