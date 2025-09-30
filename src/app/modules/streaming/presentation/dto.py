from pydantic import BaseModel


class CardiotocographyPointDTO(BaseModel):
    bpm: float
    uc: float
    timestamp: float


class TimeRangeDTO(BaseModel):
    start: int
    end: int


class ProcessDTO(BaseModel):
    tachycardia: str
    hypoxia_proba: float | None
    accelerations: list[TimeRangeDTO]
    decelerations: list[TimeRangeDTO]
    median_fhr_10min: float | None
    current_fhr: float | None
    current_uterus: float | None
    stv_5min: float | None
    time_sec: int
