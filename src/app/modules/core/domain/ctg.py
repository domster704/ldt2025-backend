from dataclasses import dataclass
from datetime import datetime
from os import PathLike


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
    accellations: int
    deceleration: int
    uterine_contractions: int
    fetal_movements: int
    fetal_movements_little: int
    accellations_little: int
    deceleration_little: int
    high_variability: int
    low_variability: int
    loss_signals: float
    timestamp: datetime


@dataclass(slots=True)
class CTGHistory:
    id: int | None
    dir_path: PathLike
    archive_path: PathLike | None
    result: CTGResult | None = None
