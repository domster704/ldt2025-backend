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
    stv_forecast: Optional[dict[str, Optional[float]]]
    median_fhr_10min: Optional[float]
    hypoxia_proba: Optional[float]
    savelyeva_score: Optional[int]
    savelyeva_category: Optional[str]
    fischer_score: Optional[int]
    fischer_category: Optional[str]
    accelerations_count: int
    decelerations_count: int


class ProcessResultsDTO(BaseModel):
    last_figo: Optional[str]
    last_savelyeva: Optional[int]
    last_savelyeva_category: Optional[str]
    last_fischer: Optional[int]
    last_fischer_category: Optional[str]
    baseline_bpm: Optional[float]
    stv_all: Optional[float]
    stv_10min_mean: Optional[float]
    accelerations_count: int
    decelerations_count: int
    uterus_mean: Optional[float]

