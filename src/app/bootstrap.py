from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from app.common.container import build_container
from app.common.settings.web import WebServerSettings, RunMode, web_settings
from app.logger import setup_logger
from app.middlewares import HTTPLogMiddleware

# from app.modules.core.router import router as core_router # type: ignore
from app.modules.auth.router import router as auth_router
from app.modules.monitoring.health.router import router as health_router

ROUTERS = [
    health_router,
    # core_router,
    auth_router,
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await app.state.dishka_container.close()


def create_app(env_name: str = ".env") -> tuple[FastAPI, WebServerSettings]:
    container = build_container(env_name)

    def _is_dev() -> bool:
        return web_settings.RUN_MODE == RunMode.DEV

    app = FastAPI(
        title="woym-market-server",
        root_path="/backend",
        version=web_settings.API_VERSION,
        docs_url=None if _is_dev() else "/docs",
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
        allow_origins=web_settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        app.include_router(router)

    return app, web_settings