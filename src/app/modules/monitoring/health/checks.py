import httpx
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from app.modules.monitoring.health.aggregation import CheckResult, HealthCheck, HealthStatus


def db_check(engine: AsyncEngine, name: str = "db", critical: bool = True) -> HealthCheck:
    async def _run() -> CheckResult:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return CheckResult(name=name, status=HealthStatus.GREEN, critical=critical)
        except Exception as e:
            return CheckResult(name=name, status=HealthStatus.RED, critical=critical, details={"error": str(e)})
    return _run

def keycloak_check(issuer: str, timeout: float = 2.0, name: str = "keycloak", critical: bool = True) -> HealthCheck:
    async def _run() -> CheckResult:
        well_known = issuer.rstrip("/") + "/.well-known/openid-configuration"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(well_known)
                ok = r.status_code < 500
            return CheckResult(name=name, status=HealthStatus.GREEN if ok else HealthStatus.RED, critical=critical)
        except Exception as e:
            return CheckResult(name=name, status=HealthStatus.RED, critical=critical, details={"error": str(e)})
    return _run