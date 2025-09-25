from fastapi import APIRouter

from app.modules.core.infra.routes.extract_signals import router as extract_signals_router

router = APIRouter()

router.include_router(extract_signals_router)