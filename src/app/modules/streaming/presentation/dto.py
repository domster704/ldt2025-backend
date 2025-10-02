from enum import Enum
from typing import Optional

from pydantic import BaseModel


class CardiotocographyPointDTO(BaseModel):
    bpm: float
    uc: float
    timestamp: float


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    PURPLE = "purple"


class TimeRangeDTO(BaseModel):
    start: int
    end: int


class NotificationDTO(BaseModel):
    message: str
    color: Color


class ProcessDTO(BaseModel):
    time_sec: int
    current_status: Optional[str]
    notifications: dict[int, list[NotificationDTO]]
    figo_situation: Optional[str]
    current_fhr: Optional[float]
    current_uterus: Optional[float]
    stv: Optional[float]
    stv_forecast: Optional[dict[str, Optional[float]]]  # <-- теперь допускается None
    median_fhr_10min: Optional[float]
    hypoxia_proba: Optional[float]


class ProcessResultsDTO(BaseModel):
    last_figo: Optional[str]
    baseline_bpm: Optional[float]
    stv_all: Optional[float]
    stv_10min_mean: Optional[float]
    accelerations_count: int
    decelerations_count: int
    uterus_mean: Optional[float]


class ProcessInputPointDTO(BaseModel):
    time_sec: float
    value_bpm: float
    value_uterus: float
