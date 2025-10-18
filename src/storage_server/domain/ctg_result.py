from dataclasses import fields
from typing import Mapping, Any

from dataclasses import dataclass
from pydantic import BaseModel

from storage_server.domain.mixin import DataclassMixin


@dataclass(frozen=True, slots=True)
class CTGResult(DataclassMixin):
    ctg_id: int | None
    gest_age: str
    bpm: float
    uc: float
    figo: str
    figo_prognosis: str
    bhr: float
    amplitude_oscillations: float
    oscillation_frequency: float
    ltv: int
    stv: int
    stv_little: int
    accelerations: int
    decelerations: int
    uterine_contractions: int
    fetal_movements: int
    fetal_movements_little: int
    accelerations_little: int
    deceleration_little: int
    high_variability: int
    low_variability: int
    loss_signals: float

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'CTGResult':
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}

        return CTGResult(**filtered)

    @staticmethod
    def from_dto(model: BaseModel) -> 'CTGResult':
        data = model.model_dump()
        return CTGResult(**data)
