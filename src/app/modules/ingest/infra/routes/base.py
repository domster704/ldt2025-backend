from fastapi import APIRouter

from .medical_signals import router as medical_signals_router

router = APIRouter()

router.include_router(medical_signals_router)