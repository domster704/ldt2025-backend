from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd


def slice_last_seconds(arr, now_t, seconds):
    lo = now_t - seconds + 1
    lo = max(0, lo)
    if isinstance(arr, deque):
        vals = [v for (t, v) in arr if t >= lo and t <= now_t and pd.notna(v)]
    else:
        vals = arr[lo : now_t + 1]
    return vals


def median_last_seconds(arr, now_t, seconds):
    vals = slice_last_seconds(arr, now_t, seconds)
    return float(np.median(vals)) if len(vals) > 0 else None


def calculate_stv(fhr: np.ndarray, fs: int = 5) -> float:
    if fhr is None or len(fhr) == 0:
        return np.nan
    minutes = len(fhr) // (fs * 60)
    if minutes <= 0:
        return np.nan
    chunks = np.array_split(fhr, 16 * minutes)
    means = np.array([np.nanmean(c) if len(c) else np.nan for c in chunks])
    if len(means) < 2:
        return np.nan
    diffs = np.abs(np.diff(means))
    return float(np.nanmean(diffs))


def mean_last_second(df, end_second):
    start = end_second - 1
    sl = df[(df["time_sec"] > start) & (df["time_sec"] <= end_second)]
    return sl["value_bpm"].mean(), sl["value_uterus"].mean()


def rolling_stv_mean_10min(fhr: np.ndarray, fs: int = 5) -> float:
    if fhr is None or len(fhr) < fs * 600:
        return np.nan
    win = fs * 600
    step = fs * 60
    stvs = []
    for start in range(0, len(fhr) - win + 1, step):
        stv = calculate_stv(fhr[start : start + win], fs=fs)
        if not np.isnan(stv):
            stvs.append(stv)
    return float(np.nanmean(stvs)) if stvs else np.nan
