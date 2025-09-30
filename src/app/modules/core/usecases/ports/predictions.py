from asyncio import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.infra.routes.ws.prediction import Prediction


class PredictionsPort(Protocol):
    def __init__(self, session: AsyncSession) -> None: ...

    def save(self, prediction: Prediction) -> None: ...