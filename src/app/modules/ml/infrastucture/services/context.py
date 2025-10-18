from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.modules.ml.infrastucture.services.fetal_monitoring import (
    HypoxiaModelConfig,
    STVModelsConfig,
)
from app.modules.ml.infrastucture.services.utils import mean_last_second


class NotificationCenter:
    def __init__(self):
        self.notifications: Dict[int, List[Dict[str, str]]] = {}
        self.last_notification: Dict[str, Any] = {
            "tachycardia": "Недостаточно данных",
            "hypoxia_proba": None,
            "hypoxia_proba_ewma": None,
            # детальные события
            "accelerations": [],
            "decelerations": [],
            # обнаруженные схватки (по UC)
            "contractions": [],
            # оценка по Савельевой
            "savelyeva_score": None,
            "savelyeva_category": None,  # "Норма" | "Начальные нарушения" | "Выраженные изменения"
            "fischer_score": None,
            "fischer_category": None,
            "median_fhr_10min": None,
            "current_fhr": None,
            "current_uterus": None,
            "stv": None,
            "stv_forecast": None,
            "figo_situation": None,
            "notifications": {},
            "current_status": None,
            "time_sec": 0,
        }

    def notify(self, now_t: int, message: str, color: str = "yellow"):
        if now_t not in self.notifications:
            self.notifications[now_t] = []
        self.notifications[now_t].append({"message": message, "color": color})


@dataclass
class StreamContext:
    # time & data
    now_t: int = 0
    current_df: Optional[pd.DataFrame] = None

    # second-wise buffers (ring)
    sec_fhr: Deque[Tuple[int, float]] = field(
        default_factory=lambda: deque(maxlen=30 * 5 * 60)
    )
    sec_uc: Deque[Tuple[int, float]] = field(
        default_factory=lambda: deque(maxlen=30 * 5 * 60)
    )

    # states/flags
    state_flags: Dict[str, Any] = field(
        default_factory=lambda: {
            "tachy_active": False,
            "brady_active": False,
            "hypoxia_active": False,
            "figo_last": None,
        }
    )
    active_accel: Optional[Dict[str, Any]] = None
    active_decel: Optional[Dict[str, Any]] = None

    # configs & models
    stv_cfg: STVModelsConfig = None  # type: ignore
    hypoxia_cfg: HypoxiaModelConfig = None  # type: ignore

    # io / events
    nc: NotificationCenter = field(default_factory=NotificationCenter)

    # parameters
    fs: int = 5
    accel_delta_bpm: int = 15
    decel_delta_bpm: int = -15
    min_event_duration_sec: int = 15
    local_baseline_window_sec: int = 60
    tachy_threshold_bpm: int = 160
    tachy_eval_every_sec: int = 10
    brady_threshold_bpm: int = 110
    brady_eval_every_sec: int = 10

    def mean_last_second(self) -> Tuple[float, float]:
        if self.current_df is None or self.current_df.empty:
            return (np.nan, np.nan)
        return mean_last_second(self.current_df, self.now_t)

    def create_window_df(self) -> pd.DataFrame:
        w = self.stv_cfg["window_size"]
        df = self.current_df
        sl = df[
            (df["time_sec"] >= self.now_t - w) & (df["time_sec"] <= self.now_t)
        ].copy()
        sl["window_time_max"] = self.now_t
        return sl
