from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: int
    end: int


class Color(Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    PURPLE = "purple"


@dataclass(frozen=True, slots=True)
class Notification:
    message: str
    color: Color


@dataclass(frozen=True, slots=True)
class Process:
    time_sec: int
    current_status: str | None
    notifications: dict[int, list[Notification]]
    figo_situation: str | None
    current_fhr: float | None
    current_uterus: float | None
    stv: float | None
    stv_forecast: dict[str, float | None]
    median_fhr_10min: float | None
    hypoxia_proba: float | None
    savelyeva_score: int | None
    savelyeva_category: str | None
    fischer_score: int | None
    fischer_category: str | None
    accelerations_count: int
    decelerations_count: int


@dataclass(frozen=True, slots=True)
class ProcessResults:
    last_figo: str | None
    last_savelyeva: int | None
    last_savelyeva_category: str | None
    last_fischer: int | None
    last_fischer_category: str | None
    baseline_bpm: float | None
    stv_all: float | None
    stv_10min_mean: float | None
    accelerations_count: int
    decelerations_count: int
    uterus_mean: float | None


@dataclass(frozen=True, slots=True)
class ProcessInputPoint:
    time_sec: float
    value_bpm: float
    value_uterus: float
