from fastapi import APIRouter

from app.modules.core.infra.routes.extract_signals import router as extract_signals_router
from app.modules.core.infra.routes.get_patient import router as patient_router
from app.modules.core.infra.routes.get_ctg_history import router as ctg_history_router

router = APIRouter()

router.include_router(extract_signals_router)
router.include_router(patient_router)
router.include_router(ctg_history_router)