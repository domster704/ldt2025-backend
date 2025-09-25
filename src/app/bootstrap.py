from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from app.common.container import build_container
from app.common.settings.web import RunMode, app_settings, http_server_settings
from app.logger import setup_logger
from app.middlewares import HTTPLogMiddleware

from app.modules.core.infra.routes.base import router as core_router
# from app.modules.auth.router import router as auth_router
from app.modules.monitoring.health.router import router as health_router

ROUTERS = [
    health_router,
    core_router,
    # auth_router,
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await app.state.dishka_container.close()


def create_app(env_name: str = ".env") -> FastAPI:
    container = build_container(env_name)

    def _is_dev() -> bool:
        return app_settings.run_mode == RunMode.DEV

    app = FastAPI(
        title="woym-market-server",
        root_path="/backend",
        version=http_server_settings.api_version,
        docs_url=None if not _is_dev() else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    setup_dishka(container, app)
    setup_logger(_is_dev())

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
        app.include_router(router)

    return app