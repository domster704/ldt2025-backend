from datetime import datetime
from typing import Any

import pytz
from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import FromDishka, inject
from app.modules.monitoring.health.aggregation import aggregate, HealthStatus, HealthCheck

router = APIRouter()

@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "alive",
        "timestamp": datetime.now(tz=pytz.timezone('Europe/Moscow')).isoformat(),
    }

@router.get("/ready")
@inject
async def ready(checks: FromDishka[list[HealthCheck]]) -> dict[str, Any]:
    result = await aggregate(checks)
    if result["status"] == HealthStatus.RED:
        raise HTTPException(status_code=503, detail=result)
    result['timestamp'] = datetime.now(tz=pytz.timezone('Europe/Moscow')).isoformat()
    return result