import numpy as np
import pandas as pd
from scipy import signal
from scipy.stats import kurtosis, skew


def detect_baseline(fhr, window_size=50):
    """Calculate baseline FHR using moving median"""
    if len(fhr) < window_size:
        return np.median(fhr)
    return np.median(
        pd.Series(fhr).rolling(window=window_size, center=True, min_periods=1).median()
    )


def detect_accelerations(fhr, baseline, threshold=15, duration=2):
    """
    Detect accelerations (increases above baseline)

    Returns:
        acceleration_count: number of accelerations
        max_acceleration: maximum amplitude
        total_acceleration_duration: total duration in samples
    """
    if len(fhr) == 0:
        return 0, 0, 0

    above_threshold = fhr > (baseline + threshold)
    acceleration_count = 0
    max_acceleration = 0
    total_acceleration_duration = 0

    i = 0
    while i < len(above_threshold):
        if above_threshold[i]:
            start = i
            while i < len(above_threshold) and above_threshold[i]:
                i += 1
            duration_samples = i - start
            if duration_samples >= duration:
                acceleration_count += 1
                total_acceleration_duration += duration_samples
                max_acceleration = max(
                    max_acceleration, np.max(fhr[start:i]) - baseline
                )
        i += 1

    return acceleration_count, max_acceleration, total_acceleration_duration


def detect_decelerations(fhr, uc, baseline, threshold=15, duration=2):
    """
    Detect decelerations (decreases below baseline)
    Critical feature for hypoxia detection!

    Returns:
        deceleration_count: total number of decelerations
        max_deceleration: maximum depth
        total_deceleration_duration: total duration
        late_decelerations: count of late decelerations (after UC peak)
        variable_decelerations: count of variable decelerations
    """
    if len(fhr) == 0:
        return 0, 0, 0, 0, 0

    below_threshold = fhr < (baseline - threshold)
    deceleration_count = 0
    max_deceleration = 0
    total_deceleration_duration = 0
    late_decelerations = 0
    variable_decelerations = 0

    # Find UC peaks for late deceleration detection
    try:
        uc_peaks = (
            signal.find_peaks(uc, height=np.percentile(uc, 70))[0]
            if len(uc) > 10
            else []
        )
    except:
        uc_peaks = []

    i = 0
    while i < len(below_threshold):
        if below_threshold[i]:
            start = i
            while i < len(below_threshold) and below_threshold[i]:
                i += 1
            duration_samples = i - start
            if duration_samples >= duration:
                deceleration_count += 1
                total_deceleration_duration += duration_samples
                max_deceleration = max(
                    max_deceleration, baseline - np.min(fhr[start:i])
                )

                # Check if it's a late deceleration (after UC peak)
                decel_center = (start + i) // 2
                is_late = False
                for peak in uc_peaks:
                    if (
                        peak < decel_center < peak + 30
                    ):  # Late if within 30 samples after UC peak
                        late_decelerations += 1
                        is_late = True
                        break
                if not is_late:
                    variable_decelerations += 1
        i += 1

    return (
        deceleration_count,
        max_deceleration,
        total_deceleration_duration,
        late_decelerations,
        variable_decelerations,
    )


def calculate_variability_metrics(fhr):
    """
    Calculate short-term and long-term variability

    Returns:
        stv: short-term variability
        ltv: long-term variability
        cv: coefficient of variation
        skewness: distribution skewness
        kurt: kurtosis
    """
    if len(fhr) < 2:
        return 0, 0, 0, 0, 0

    # Short-term variability (STV)
    diff = np.diff(fhr)
    stv = np.mean(np.abs(diff)) if len(diff) > 0 else 0

    # Long-term variability (LTV) - variability over longer segments
    if len(fhr) >= 60:
        segment_size = len(fhr) // 6
        segment_means = [
            np.mean(fhr[i : i + segment_size])
            for i in range(0, len(fhr), segment_size)
            if i + segment_size <= len(fhr)
        ]
        ltv = np.std(segment_means) if len(segment_means) > 1 else 0
    else:
        ltv = 0

    # Additional variability metrics
    cv = (
        np.std(fhr) / np.mean(fhr) if np.mean(fhr) > 0 else 0
    )  # Coefficient of variation
    try:
        skewness = skew(fhr)
        kurt = kurtosis(fhr)
    except:
        skewness = 0
        kurt = 0

    return stv, ltv, cv, skewness, kurt


def calculate_trend_features(fhr, uc):
    """Calculate trend and rate of change features"""
    if len(fhr) < 2:
        return 0, 0, 0, 0

    # Linear trend
    x = np.arange(len(fhr))
    try:
        fhr_trend = np.polyfit(x, fhr, 1)[0] if len(fhr) > 1 else 0
        uc_trend = np.polyfit(x, uc, 1)[0] if len(uc) > 1 else 0
    except:
        fhr_trend = 0
        uc_trend = 0

    # Rate of change
    fhr_roc = (fhr[-1] - fhr[0]) / len(fhr) if len(fhr) > 0 else 0

    # Variability trend (is variability increasing or decreasing?)
    if len(fhr) >= 20:
        first_half_std = np.std(fhr[: len(fhr) // 2])
        second_half_std = np.std(fhr[len(fhr) // 2 :])
        variability_trend = second_half_std - first_half_std
    else:
        variability_trend = 0

    return fhr_trend, uc_trend, fhr_roc, variability_trend


def calculate_uc_features(uc):
    """Calculate uterine contraction specific features"""
    if len(uc) < 10:
        return 0, 0, 0, 0

    # Find contraction peaks
    try:
        peaks, properties = signal.find_peaks(
            uc, height=np.percentile(uc, 70), distance=20
        )
    except:
        return 0, 0, 0, 0

    uc_frequency = (
        len(peaks) / (len(uc) / 300) if len(uc) > 0 else 0
    )  # Contractions per 5 min
    uc_peak_mean = np.mean(properties["peak_heights"]) if len(peaks) > 0 else 0
    uc_peak_max = np.max(properties["peak_heights"]) if len(peaks) > 0 else 0

    # Contraction regularity (lower std = more regular)
    if len(peaks) > 1:
        intervals = np.diff(peaks)
        uc_regularity = (
            np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
        )
    else:
        uc_regularity = 0

    return uc_frequency, uc_peak_mean, uc_peak_max, uc_regularity


def extract_features(window_df):
    """
    Extract comprehensive features from window

    Args:
        window_df: DataFrame with columns 'value_bpm', 'value_uterus', 'window_time_max'

    Returns:
        Dictionary of 40+ features
    """
    if window_df.empty:
        return {}

    fhr = window_df["value_bpm"].values
    uc = window_df["value_uterus"].values
    window_time = window_df["window_time_max"].values[0]

    # Basic statistics
    median_fhr = np.median(fhr)
    mean_fhr = np.mean(fhr)
    std_fhr = np.std(fhr)
    min_fhr = np.min(fhr)
    max_fhr = np.max(fhr)
    range_fhr = max_fhr - min_fhr

    median_uc = np.median(uc)
    mean_uc = np.mean(uc)
    std_uc = np.std(uc)
    min_uc = np.min(uc)
    max_uc = np.max(uc)

    # Traditional HRV metrics
    rr_diff = np.diff(fhr)
    sdnn = np.std(fhr)
    rmssd = np.sqrt(np.mean(rr_diff**2)) if len(rr_diff) > 0 else 0
    pnn50 = np.mean(np.abs(rr_diff) > 50) if len(rr_diff) > 0 else 0

    # Baseline detection
    baseline = detect_baseline(fhr)

    # Accelerations
    acc_count, acc_max, acc_duration = detect_accelerations(fhr, baseline)

    # Decelerations (critical for hypoxia!)
    dec_count, dec_max, dec_duration, late_dec, var_dec = detect_decelerations(
        fhr, uc, baseline
    )

    # Variability metrics
    stv, ltv, cv, skewness, kurt = calculate_variability_metrics(fhr)

    # Trend features
    fhr_trend, uc_trend, fhr_roc, var_trend = calculate_trend_features(fhr, uc)

    # UC features
    uc_freq, uc_peak_mean, uc_peak_max, uc_regularity = calculate_uc_features(uc)

    # FHR-UC correlation
    try:
        uc_corr = (
            np.corrcoef(fhr, uc)[0, 1] if np.std(uc) > 0 and np.std(fhr) > 0 else 0
        )
    except:
        uc_corr = 0

    return {
        # Basic FHR statistics
        "median_fhr": median_fhr,
        "mean_fhr": mean_fhr,
        "std_fhr": std_fhr,
        "min_fhr": min_fhr,
        "max_fhr": max_fhr,
        "range_fhr": range_fhr,
        "baseline_fhr": baseline,
        # Basic UC statistics
        "median_uc": median_uc,
        "mean_uc": mean_uc,
        "std_uc": std_uc,
        "min_uc": min_uc,
        "max_uc": max_uc,
        # Traditional HRV
        "sdnn": sdnn,
        "rmssd": rmssd,
        "pnn50": pnn50,
        # Accelerations
        "acceleration_count": acc_count,
        "acceleration_max": acc_max,
        "acceleration_duration": acc_duration,
        # Decelerations (KEY FEATURES!)
        "deceleration_count": dec_count,
        "deceleration_max": dec_max,
        "deceleration_duration": dec_duration,
        "late_deceleration_count": late_dec,
        "variable_deceleration_count": var_dec,
        # Variability metrics
        "stv": stv,
        "ltv": ltv,
        "cv": cv,
        "skewness": skewness,
        "kurtosis": kurt,
        # Trend features
        "fhr_trend": fhr_trend,
        "uc_trend": uc_trend,
        "fhr_roc": fhr_roc,
        "variability_trend": var_trend,
        # UC features
        "uc_frequency": uc_freq,
        "uc_peak_mean": uc_peak_mean,
        "uc_peak_max": uc_peak_max,
        "uc_regularity": uc_regularity,
        # Coupling
        "uc_corr": uc_corr,
        # Meta
        "window_time_max": window_time,
    }
