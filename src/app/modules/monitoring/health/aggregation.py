from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Dict, List

class HealthStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

@dataclass(frozen=True)
class CheckResult:
    name: str
    status: HealthStatus
    details: Dict[str, str] | None = None
    critical: bool = True

HealthCheck = Callable[[], Awaitable[CheckResult]]

async def aggregate(checks: List[HealthCheck]) -> dict:
    results = [await c() for c in checks]
    overall = HealthStatus.GREEN
    if any(r.status == HealthStatus.RED and r.critical for r in results):
        overall = HealthStatus.RED
    elif any(r.status == HealthStatus.YELLOW or r.status == HealthStatus.RED for r in results):
        overall = HealthStatus.YELLOW
    return {
        "status": overall,
        "checks": [
            {"name": r.name, "status": r.status, "critical": r.critical, "details": r.details or {}}
            for r in results
        ],
    }