from app.modules.monitoring.health.aggregation import HealthCheck
from app.modules.monitoring.health.checks import keycloak_check, db_check
from sqlalchemy.ext.asyncio import AsyncEngine
from app.common.settings import KeycloakSettings


def make_auth_checks(engine: AsyncEngine, kc: KeycloakSettings) -> list[HealthCheck]:
    return [
        db_check(engine, name="auth-db", critical=True),
        keycloak_check(issuer=kc.issuer, name="keycloak", critical=True),
    ]