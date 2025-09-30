from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from starlette.websockets import WebSocket

router = APIRouter()

@dataclass(frozen=True, slots=True)
class Prediction:
    type: Literal["bmp", "uc"]
    time: int
    value: Decimal

@router.websocket('/ingest')
async def ingest_prediction(websocket: WebSocket):
    """ Получение предсказаний с ручки """
    # сохранение предсказаний в SQLite
