from fastapi import APIRouter

from app.modules.streaming.presentation.router.streaming_router import streaming_router
from app.modules.streaming.presentation.router.result_router import router as result_router

router = APIRouter()
router.include_router(streaming_router, prefix="/ws/streaming")
router.include_router(result_router, prefix="/ctg-result")
