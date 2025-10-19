from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CTGResult:
    ctg_id: int
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
    deceleration: int
    uterine_contractions: int
    fetal_movements: int
    fetal_movements_little: int
    accelerations_little: int
    deceleration_little: int
    high_variability: int
    low_variability: int
    loss_signals: float
    timestamp: datetime
    fischer_status: str = 'string'
    savelyeva_status: str = 'string'

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CTGResult":
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return CTGResult(**filtered)


@dataclass(slots=True)
class CTGHistory:
    id: int | None
    file_path_in_archive: PathLike[str]
    archive_path: PathLike[str] | None = None
    ctg_result: CTGResult | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CTGHistory":
        if data.get('result'):
            result_dict = data['result']
            ctg_result = CTGResult(**result_dict)
        else:
            ctg_result = None
        data_dict = {
            'result': ctg_result,
            **data
        }

        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data_dict.items() if k in allowed}
        return CTGHistory(**filtered)

    def set_archive_path(self, archive_path: PathLike) -> None:
        self.archive_path = archive_path

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'CTGHistory':
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}

        return CTGHistory(**filtered)
