from fastapi import APIRouter

from app.modules.core.infra.routes.http.extract_signals import router as extract_signals_router

router = APIRouter()

router.include_router(extract_signals_router)