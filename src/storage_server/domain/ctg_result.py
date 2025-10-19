from dataclasses import fields
from typing import Mapping, Any

from dataclasses import dataclass
from pydantic import BaseModel

from storage_server.domain.mixin import DataclassMixin


@dataclass(frozen=True, slots=True)
class CTGResult(DataclassMixin):
    ctg_id: int | None
    gest_age: str | None
    bpm: float | None
    uc: float | None
    figo: str | None
    figo_prognosis: str | None
    bhr: float | None
    amplitude_oscillations: float | None
    oscillation_frequency: float | None
    ltv: int | None
    stv: int | None
    stv_little: int | None
    accelerations: int | None
    decelerations: int | None
    uterine_contractions: int | None
    fetal_movements: int | None
    fetal_movements_little: int | None
    accelerations_little: int | None
    deceleration_little: int | None
    high_variability: int | None
    low_variability: int | None
    loss_signals: float | None
    fischer_status: str | None
    savelyeva_status: str | None

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'CTGResult':
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}

        return CTGResult(**filtered)

    @staticmethod
    def from_dto(model: BaseModel) -> 'CTGResult':
        data = model.model_dump()
        return CTGResult(**data)
