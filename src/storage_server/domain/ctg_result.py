from typing import Mapping, Any

from attr import dataclass
from pydantic import BaseModel

from storage_server.domain.mixin import DataclassMixin


@dataclass(slots=True, frozen=True)
class CTGResult(DataclassMixin):
    id: int | None
    slope_bpm_min: float
    sdnn: float
    rmssd: float
    pnn5: float
    baseline_med: float
    vmin: float
    vmax: float
    missing_ratio: float
    est_fs: float

    @staticmethod
    def from_db_row(row: Mapping[str, Any]) -> 'CTGResult':
        return CTGResult(**row)

    @staticmethod
    def from_dto(model: BaseModel) -> 'CTGResult':
        data = model.model_dump()
        return CTGResult(
            slope_bpm_min = data.get("slope_bpm_min"),
            sdnn = data.get("sdnn"),
            rmssd = data.get("rmssd"),
            pnn5 = data.get("pnn5"),
            baseline_med = data.get("baseline_med"),
            vmin = data.get("vmin"),
            vmax = data.get("vmax"),
            missing_ratio = data.get("missing_ratio"),
            est_fs = data.get("est_fs")
        )
