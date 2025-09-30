from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Process:
    tachycardia: str
    hypoxia_proba: float | None
    accelerations: list[TimeRange]
    decelerations: list[TimeRange]
    median_fhr_10min: float | None
    current_fhr: float | None
    current_uterus: float | None
    stv_5min: float | None
    time_sec: int


@dataclass(frozen=True, slots=True)
class ProcessInputPoint:
    time_sec: float
    value_bpm: float
    value_uterus: float
