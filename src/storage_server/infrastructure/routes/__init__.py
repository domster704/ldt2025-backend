from fastapi import APIRouter

from .patient import router as patient_router
from .ctg_history import router as ctg_history_router
from .ctg_result import router as ctg_result_router
from .ctg_graphic_archive import router as ctg_graphic_router

ROUTERS: list[tuple[APIRouter, str | None]] = [
    (patient_router, "/patients"),
    (ctg_history_router, "/ctg_history"),
    (ctg_graphic_router, "/ctg_graphic")
]