from fastapi import APIRouter

from .patient import router as patient_router

ROUTERS: list[tuple[APIRouter, str | None]] = [
    (patient_router, "/patients"),
]