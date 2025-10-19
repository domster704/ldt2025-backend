from __future__ import annotations

from typing import Optional, Protocol

import numpy as np
import pandas as pd

from app.modules.ml.infrastucture.services.context import StreamContext
from app.modules.ml.infrastucture.services.features import extract_features
from app.modules.ml.infrastucture.services.utils import (
    calculate_stv,
    median_last_seconds,
    slice_last_seconds,
)


class Stage(Protocol):
    def tick(self, ctx: StreamContext) -> None: ...


class IngestionStage:
    """Обрабатывает новые данные"""

    def tick(self, ctx: StreamContext) -> None:
        ctx.now_t += 1
        if ctx.current_df is not None:
            ctx.current_df = ctx.current_df[
                ctx.current_df["time_sec"] <= ctx.now_t
            ].copy()

        curr_fhr, curr_uc = ctx.mean_last_second()
        ctx.sec_fhr.append(
            (ctx.now_t, float(curr_fhr) if pd.notna(curr_fhr) else np.nan)
        )
        ctx.sec_uc.append((ctx.now_t, float(curr_uc) if pd.notna(curr_uc) else np.nan))

        ctx.nc.last_notification["current_fhr"] = (
            None if pd.isna(curr_fhr) else float(round(curr_fhr, 2))
        )
        ctx.nc.last_notification["current_uterus"] = (
            None if pd.isna(curr_uc) else float(round(curr_uc, 2))
        )
        ctx.nc.last_notification["time_sec"] = ctx.now_t


class TachyBradyStage:
    """Оценивает тахикардию и брадикардию."""

    def tick(self, ctx: StreamContext) -> None:
        # Tachy (every N sec)
        if ctx.now_t % ctx.tachy_eval_every_sec == 0:
            median_10 = median_last_seconds(ctx.sec_fhr, ctx.now_t, 600)
            ctx.nc.last_notification["median_fhr_10min"] = median_10

            if median_10 is None:
                ctx.nc.last_notification["tachycardia"] = "Недостаточно данных"
                ctx.state_flags["tachy_active"] = False
            elif median_10 > ctx.tachy_threshold_bpm:
                deviation = round(median_10 - ctx.tachy_threshold_bpm, 1)
                ctx.nc.last_notification["tachycardia"] = (
                    f"Подозрение на тахикардию (базальная ≈ {median_10:.1f} bpm, +{deviation} bpm)."
                )
                if not ctx.state_flags["tachy_active"]:
                    ctx.nc.notify(
                        ctx.now_t,
                        f"Тахикардия: базальная ≈ {median_10:.1f} bpm",
                        color="red",
                    )
                    ctx.state_flags["tachy_active"] = True
            else:
                ctx.nc.last_notification["tachycardia"] = (
                    f"Нет признаков тахикардии (базальная ≈ {median_10:.1f} bpm)."
                )
                if ctx.state_flags["tachy_active"]:
                    ctx.nc.notify(ctx.now_t, "Тахикардия прекратилась", color="green")
                ctx.state_flags["tachy_active"] = False

        # Brady (every M sec)
        if ctx.now_t % ctx.brady_eval_every_sec == 0:
            median_10 = ctx.nc.last_notification["median_fhr_10min"]
            if median_10 is not None:
                if median_10 < ctx.brady_threshold_bpm:
                    if not ctx.state_flags["brady_active"]:
                        ctx.nc.notify(
                            ctx.now_t,
                            f"Брадикардия: базальная ≈ {median_10:.1f} bpm",
                            color="red",
                        )
                        ctx.state_flags["brady_active"] = True
                else:
                    if ctx.state_flags["brady_active"]:
                        ctx.nc.notify(
                            ctx.now_t, "Брадикардия прекратилась", color="green"
                        )
                    ctx.state_flags["brady_active"] = False


class STV10MinStage:
    """Вычисляет STV за последние 10 минут каждые 10 секунд."""

    def tick(self, ctx: StreamContext) -> None:
        if ctx.now_t % 10 != 0:
            return
        if ctx.current_df is None or ctx.current_df.empty:
            ctx.nc.last_notification["stv"] = None
            return
        last_10_fhr = slice_last_seconds(
            ctx.current_df["value_bpm"].values, ctx.now_t, 600
        )
        stv = calculate_stv(np.array(last_10_fhr), fs=ctx.fs)
        ctx.nc.last_notification["stv"] = (
            None if np.isnan(stv) else float(round(stv, 2))
        )


class ModelsStage:
    """STV прогнозы (3/5/10m) и вероятность гипоксии на скользящем окне признаков."""

    def tick(self, ctx: StreamContext) -> None:
        step = ctx.stv_cfg["step_size"]
        if ctx.now_t % step != 0:
            return
        if ctx.now_t < ctx.stv_cfg["window_size"]:
            return
        window_df = ctx.create_window_df()
        if window_df.empty:
            return

        feats = extract_features(window_df)
        model_input = pd.DataFrame([feats])

        # --- STV forecasts ---
        forecasts = {"stv_3m": None, "stv_5m": None, "stv_10m": None}
        for name, spec in ctx.stv_cfg["models"].items():
            val = spec["model"].predict(model_input).item()
            forecasts[name] = float(val) if val is not None else None

        # --- Hypoxia proba + EWMA ---
        proba = ctx.hypoxia_cfg.model.predict_proba(model_input)[:, 1].item()
        ewma = self._update_ewma(ctx, proba)
        ctx.nc.last_notification["hypoxia_proba"] = ewma
        ctx.nc.last_notification["stv_forecast"] = forecasts

        # notifications on threshold crossing
        if ewma is not None and ewma >= 0.8:
            if not ctx.state_flags["hypoxia_active"]:
                ctx.nc.notify(
                    ctx.now_t, f"Высокая вероятность гипоксии: {ewma:.2f}", color="red"
                )
                ctx.state_flags["hypoxia_active"] = True
        else:
            if ctx.state_flags["hypoxia_active"]:
                ctx.nc.notify(
                    ctx.now_t, "Вероятность гипоксии снизилась", color="green"
                )
            ctx.state_flags["hypoxia_active"] = False

    @staticmethod
    def _update_ewma(ctx: StreamContext, proba: Optional[float]) -> Optional[float]:
        if proba is None or (isinstance(proba, float) and np.isnan(proba)):
            return ctx.nc.last_notification.get("hypoxia_proba_ewma")
        prev = ctx.nc.last_notification.get("hypoxia_proba_ewma")
        a = ctx.hypoxia_cfg.ewma_alpha
        if prev is None:
            ewma = float(proba)
        else:
            ewma = float(a * proba + (1 - a) * prev)
        ctx.nc.last_notification["hypoxia_proba_ewma"] = round(ewma, 3)
        return ctx.nc.last_notification["hypoxia_proba_ewma"]


class FigoStage:
    """FIGO классификация"""

    def tick(self, ctx: StreamContext) -> None:
        baseline = ctx.nc.last_notification["median_fhr_10min"]
        stv_10 = ctx.nc.last_notification["stv"]
        status = None
        color = "yellow"

        long_decels = any(
            (d["end"] is not None and (d["end"] - d["start"] + 1) >= 180)
            for d in ctx.nc.last_notification["decelerations"]
        )
        recent_decels = any(
            (d["end"] or ctx.now_t) >= ctx.now_t - 600
            and (d["start"]) >= ctx.now_t - 600
            for d in ctx.nc.last_notification["decelerations"]
        )

        if baseline is None or stv_10 is None:
            status = "Сомнительное"
            color = "yellow"
        else:
            if baseline < 100 or stv_10 < 1.0:
                status = "Претерминальное"
                color = "purple"
            elif (
                (baseline > 180)
                or (160 < baseline <= 180 and stv_10 < 2.0)
                or long_decels
            ):
                status = "Патологическое"
                color = "red"
            elif (
                (100 <= baseline < 110)
                or (160 <= baseline <= 180)
                or (1.0 <= stv_10 < 3.0)
                or recent_decels
            ):
                status = "Сомнительное"
                color = "yellow"
            else:
                status = "Нормальное"
                color = "green"

        ctx.nc.last_notification["figo_situation"] = status
        if status != ctx.state_flags["figo_last"]:
            ctx.nc.notify(ctx.now_t, f"Состояние FIGO: {status}", color=color)
            ctx.state_flags["figo_last"] = status


class ContractionStage:
    """
    Онлайновая детекция схваток по сигналу UC:
    - Порог по амплитуде относительно локального базиса (медиана за 120 с) + min длительность.
    """

    def __init__(self, baseline_win=120, amp_thr=15.0, min_len=30, cooldown=10):
        self.baseline_win = baseline_win
        self.amp_thr = amp_thr
        self.min_len = min_len
        self.cooldown = cooldown
        self.active = None
        self.last_end = -(10**9)

    def tick(self, ctx: StreamContext) -> None:
        if not ctx.sec_uc or ctx.sec_uc[-1][0] != ctx.now_t:
            return
        now = ctx.now_t
        uc = ctx.sec_uc[-1][1]
        if pd.isna(uc):
            return

        base = median_last_seconds(ctx.sec_uc, now, self.baseline_win)
        if base is None:
            return
        above = (uc - base) >= self.amp_thr

        # старт
        if self.active is None and above and (now - self.last_end) >= self.cooldown:
            self.active = {"start": now, "peak": now, "peak_value": uc}
        # обновление пика
        if self.active is not None:
            if uc > self.active["peak_value"]:
                self.active["peak_value"] = uc
                self.active["peak"] = now
            # завершение
            if not above:
                dur = now - self.active["start"]
                if dur >= self.min_len:
                    self.active["end"] = now
                    ctx.nc.last_notification["contractions"].append(self.active)
                    self.last_end = now
                self.active = None


class AdvancedAccelDecelStage:
    """
    Детектирует акцелерации/децелерации с измерением амплитуды и длительности,
    классифицирует децелерации: early / late / variable (по привязке к схваткам).
    """

    def __init__(
        self, local_baseline_window_sec=60, accel_thr=15.0, decel_thr=-15.0, min_len=10
    ):
        self.win = local_baseline_window_sec
        self.accel_thr = accel_thr
        self.decel_thr = decel_thr
        self.min_len = min_len
        self.accel_active = None
        self.decel_active = None

    def _nearest_contraction(self, ctx: StreamContext, t0: int, t1: int):
        # ищем схватку, перекрывающуюся по времени
        overlaps = []
        for c in ctx.nc.last_notification["contractions"]:
            if c["end"] >= t0 and c["start"] <= t1:
                overlaps.append(c)
        # берем самую "центральную"
        if not overlaps:
            return None
        return max(overlaps, key=lambda c: min(t1, c["end"]) - max(t0, c["start"]))

    def _classify_decel(self, ctx: StreamContext, start: int, end: int, amp: float):
        c = self._nearest_contraction(ctx, start, end)
        if c is None:
            return "variable", None, None
        # запаздывание: разница между началом урежения и началом схватки
        lag_start = start - c["start"]
        # позиция пика схватки относительно эпизода
        rel_peak = c["peak"] - ((start + end) // 2)

        # Эвристики по определению типов (из методички — поздние: лаг ~30–60 c, возврат после схватки)
        if lag_start >= 30 and (end >= c["end"]):
            grade = "mild" if amp <= 15 else "moderate" if amp <= 45 else "severe"
            return (
                "late",
                grade,
                {"contraction_start": c["start"], "contraction_peak": c["peak"]},
            )
        # Ранние: начало ≈ старт схватки, плавные
        if abs(lag_start) <= 10 and c["start"] <= start <= c["peak"] <= end <= c["end"]:
            return (
                "early",
                None,
                {"contraction_start": c["start"], "contraction_peak": c["peak"]},
            )
        # Иначе считаем вариабельной
        return (
            "variable",
            None,
            {"contraction_start": c["start"], "contraction_peak": c["peak"]},
        )

    def tick(self, ctx: StreamContext) -> None:
        if not ctx.sec_fhr or ctx.sec_fhr[-1][0] != ctx.now_t:
            return
        now = ctx.now_t
        curr = ctx.sec_fhr[-1][1]
        if pd.isna(curr):
            return

        base = median_last_seconds(ctx.sec_fhr, now, self.win)
        if base is None or pd.isna(base):
            return
        delta = curr - base

        # --- Акцелерации ---
        if delta >= self.accel_thr:
            if self.accel_active is None:
                self.accel_active = {"start": now, "peak": curr, "amp": 0.0}
            else:
                if curr > self.accel_active["peak"]:
                    self.accel_active["peak"] = curr
            self.accel_active["amp"] = max(self.accel_active["amp"], delta)
            ctx.active_accel = self.accel_active
        else:
            if self.accel_active is not None:
                dur = now - self.accel_active["start"]
                if dur >= self.min_len:
                    amp = float(round(self.accel_active["amp"], 1))
                    ctx.nc.last_notification["accelerations"].append(
                        {
                            "start": self.accel_active["start"],
                            "end": now - 1,
                            "amp_bpm": amp,
                            "dur_s": dur,
                        }
                    )
                    ctx.nc.notify(
                        now - 1, f"Акцелерация: +{amp} bpm, {dur}s", color="yellow"
                    )
                self.accel_active = None
                ctx.active_accel = None

        # --- Децелерации ---
        if delta <= self.decel_thr:
            if self.decel_active is None:
                self.decel_active = {"start": now, "nadir": curr, "amp": 0.0}
            else:
                if curr < self.decel_active["nadir"]:
                    self.decel_active["nadir"] = curr
            self.decel_active["amp"] = min(
                self.decel_active["amp"], delta
            )  # отрицательная
            ctx.active_decel = self.decel_active
        else:
            if self.decel_active is not None:
                dur = now - self.decel_active["start"]
                if dur >= self.min_len:
                    amp = float(round(abs(self.decel_active["amp"]), 1))
                    dec_type, grade, uc_ref = self._classify_decel(
                        ctx, self.decel_active["start"], now - 1, amp
                    )
                    ctx.nc.last_notification["decelerations"].append(
                        {
                            "start": self.decel_active["start"],
                            "end": now - 1,
                            "amp_bpm": amp,
                            "dur_s": dur,
                            "type": dec_type,
                            "grade": grade,
                            "uc_ref": uc_ref,
                        }
                    )
                    label = f"Децелерация ({dec_type}"
                    if grade:
                        label += f", {grade}"
                    label += f"): −{amp} bpm, {dur}s"
                    ctx.nc.notify(
                        now - 1, label, color="yellow" if dec_type != "late" else "red"
                    )
                self.decel_active = None
                ctx.active_decel = None

        accels_count = len(ctx.nc.last_notification["accelerations"])
        decels_count = len(ctx.nc.last_notification["decelerations"])

        ctx.nc.last_notification["accelerations_count"] = accels_count
        ctx.nc.last_notification["decelerations_count"] = decels_count


class SavelyevaScoreStage:
    """
    Шкала Фишера (модиф. Савельевой) каждые 60с по последним 10 мин.
    """

    def __init__(self, window_sec=600, eval_every=60):
        self.window_sec = window_sec
        self.eval_every = eval_every

    def _fhr_window(self, ctx: StreamContext):
        # берём из df, чтобы иметь максимальную частоту
        if ctx.current_df is None or ctx.current_df.empty:
            return None
        df = ctx.current_df
        lo = max(0, ctx.now_t - self.window_sec + 1)
        sl = df[(df["time_sec"] >= lo) & (df["time_sec"] <= ctx.now_t)]
        return sl["value_bpm"].astype(float).values if not sl.empty else None

    def _sinusoidal_like(self, fhr: np.ndarray) -> bool:
        # очень грубо: низкая вариабельность и квазисинус (1–5 циклов на 10 мин)
        if fhr is None or len(fhr) < 60:
            return False
        rng = np.nanpercentile(fhr, 95) - np.nanpercentile(fhr, 5)
        if rng < 10:  # амплитуда <10 уд/мин
            return True
        return False

    def _freq_of_osc_per_min(self, fhr: np.ndarray) -> float:
        # считаем «пересечения» вокруг сглаженной «плавающей линии»
        if fhr is None or len(fhr) < 60:
            return 0.0
        x = pd.Series(fhr).rolling(15, min_periods=1, center=True).median().values
        y = fhr - x
        signs = np.sign(y)
        crossings = np.where(np.diff(np.signbit(y)))[0]
        minutes = max(1.0, (len(fhr) / 5) / 60.0)  # ctx.fs доступен во вне, см. ниже
        return float(len(crossings) / max(1.0, minutes))

    def _amplitude_band(self, fhr: np.ndarray) -> float:
        # оценим амплитуду осцилляций как половину межквартильного размаха*1.35 ~ калибровано под 10–25
        if fhr is None or len(fhr) < 60:
            return 0.0
        p10, p90 = np.nanpercentile(fhr, 10), np.nanpercentile(fhr, 90)
        return float((p90 - p10) / 2.0)

    def _score_baseline(self, baseline: Optional[float]) -> int:
        if baseline is None:
            return 0
        if 120 <= baseline <= 160:
            return 2
        if (100 <= baseline < 120) or (160 < baseline <= 180):
            return 1
        return 0

    def _score_freq(self, freq_per_min: float) -> int:
        if freq_per_min >= 6:
            return 2
        if 3 <= freq_per_min < 6:
            return 1
        return 0

    def _score_amp(self, amp: float, sinusoidal: bool) -> int:
        if sinusoidal or amp <= 5:
            return 0
        if (5 < amp < 10) or (amp >= 25):
            return 1
        return 2  # 10–25

    def _score_accels(self, accels_last10: int) -> int:
        if accels_last10 >= 2:
            return 2  # спорадические (по таблице)
        if accels_last10 == 1:
            return 1  # периодические (условная трактовка)
        return 0

    def _score_decels(self, decels: list, now: int) -> int:
        # смотрим только последние 10 мин
        recent = [
            d
            for d in decels
            if d["start"] is not None and d["start"] >= now - self.window_sec
        ]
        if not recent:
            return 2  # отсутствуют
        # если есть ранние и нет поздних/вариабельных → 2
        if all(d.get("type") == "early" for d in recent):
            return 2
        # если есть поздние краткие/вариабельные → 1
        # считаем «краткой» < 60 с
        if any(
            (d.get("type") in ("late", "variable")) and d.get("dur_s", 0) < 60
            for d in recent
        ):
            return 1
        # поздние длительные или вариабельные выраженные → 0
        return 0

    def tick(self, ctx: StreamContext) -> None:
        if ctx.now_t % self.eval_every != 0:
            return
        fhr = self._fhr_window(ctx)
        baseline = ctx.nc.last_notification.get("median_fhr_10min")

        # частота осц/мин
        freq = self._freq_of_osc_per_min(fhr) if fhr is not None else 0.0
        # амплитуда
        amp = self._amplitude_band(fhr) if fhr is not None else 0.0
        sinus = self._sinusoidal_like(fhr) if fhr is not None else False

        # акцелерации за 10 мин
        accels10 = sum(
            1
            for a in ctx.nc.last_notification["accelerations"]
            if a["start"] >= ctx.now_t - self.window_sec
        )

        s_bas = self._score_baseline(baseline)
        s_frq = self._score_freq(freq)
        s_amp = self._score_amp(amp, sinus)
        s_acc = self._score_accels(accels10)
        s_dec = self._score_decels(ctx.nc.last_notification["decelerations"], ctx.now_t)

        total = int(s_bas + s_frq + s_amp + s_acc + s_dec)
        if total >= 8:
            cat, color = "Нормальное", "green"
        elif total >= 5:
            cat, color = "Сомнительное", "yellow"
        else:
            cat, color = "Патологическое", "red"

        if ctx.nc.last_notification["savelyeva_score"] != total:
            ctx.nc.notify(ctx.now_t, f"Савельева: {total} баллов ({cat})", color=color)

        ctx.nc.last_notification["savelyeva_score"] = total
        ctx.nc.last_notification["savelyeva_category"] = cat


class FisherClassicStage:
    """
    Классическая 10-балльная шкала Фишера (Fischer, 1976) для антенатальной КТГ.
    Оценивает каждые eval_every секунд по окну window_sec.
    Параметры (0/1/2 балла):
      - Baseline (базальная ЧСС за 10 мин): <100 или >180 -> 0; 100–110 или 160–180 -> 1; 110–160 -> 2
      - Bandwidth (амплитудная «полоса», bpm): <5 -> 0; 5–10 или >30 -> 1; 10–30 -> 2
      - Zero-crossings (частота осцилляций, пересечения нуля/мин): <2 -> 0; 2–6 -> 1; >6 -> 2
      - Accelerations: нет -> 0; периодические -> 1; спорадические -> 2
      - Decelerations: поздние -> 0; ранние -> 1; нет или вариабельные -> 2
    """

    def __init__(self, window_sec: int = 20 * 60, eval_every: int = 60):
        self.window_sec = window_sec
        self.eval_every = eval_every

    # ---- helpers ----
    def _fhr_window(self, ctx):
        if ctx.current_df is None or ctx.current_df.empty:
            return None
        lo = max(0, ctx.now_t - self.window_sec + 1)
        sl = ctx.current_df[
            (ctx.current_df["time_sec"] >= lo)
            & (ctx.current_df["time_sec"] <= ctx.now_t)
        ]
        return sl["value_bpm"].astype(float).values if not sl.empty else None

    def _bandwidth_bpm(self, fhr):
        # приближенно берем междецильный размах как «полосу» вариабельности
        if fhr is None or len(fhr) < 60:
            return 0.0
        p10, p90 = np.nanpercentile(fhr, 10), np.nanpercentile(fhr, 90)
        return float(max(0.0, p90 - p10))

    def _zero_crossings_per_min(self, fhr, fs):
        if fhr is None or len(fhr) < fs * 60:
            return 0.0
        trend = (
            pd.Series(fhr)
            .rolling(int(fs * 15), min_periods=1, center=True)
            .median()
            .values
        )
        y = fhr - trend
        crossings = np.where(np.diff(np.signbit(y)))[0]
        minutes = max(1e-9, len(fhr) / fs / 1.0 / 60.0)  # защита от деления на ноль
        return float(len(crossings) / minutes)

    def _score_baseline(self, baseline):
        if baseline is None:  # нет данных -> консервативно 0
            return 0
        if baseline < 100 or baseline > 180:
            return 0
        if (100 <= baseline <= 110) or (160 <= baseline <= 180):
            return 1
        return 2  # 110–160

    def _score_bandwidth(self, bw):
        if bw < 5:
            return 0
        if (5 <= bw <= 10) or (bw > 30):
            return 1
        return 2  # 10–30

    def _score_zero_cross(self, zc_per_min):
        if zc_per_min < 2:
            return 0
        if 2 <= zc_per_min <= 6:
            return 1
        return 2  # >6

    def _score_accels(self, ctx):
        # Эвристика под антенатальный 20-мин тест: ≥2 акцелерации за 20 мин — «реактивность есть».
        # «Периодическими» считаем частые/шаблонные (≈≥1 на 3 мин), «спорадические» — редкие, но присутствуют.
        lo = ctx.now_t - self.window_sec
        accels = [
            a
            for a in ctx.nc.last_notification["accelerations"]
            if a["start"] is not None and a["start"] >= lo
        ]
        n = len(accels)
        if n == 0:
            return 0
        per_min = n / max(1.0, self.window_sec / 60.0)
        if per_min >= (1.0 / 3.0):  # ~>=1 за 3 мин — периодические
            return 1
        return 2  # спорадические

    def _score_decels(self, ctx):
        lo = ctx.now_t - self.window_sec
        recent = [
            d
            for d in ctx.nc.last_notification["decelerations"]
            if d["start"] is not None and d["start"] >= lo
        ]
        if not recent:
            return 2  # «нет»
        if any(d.get("type") == "late" for d in recent):
            return 0
        if any(d.get("type") == "early" for d in recent):
            return 1
        return 2  # только вариабельные

    def tick(self, ctx) -> None:
        if ctx.now_t % self.eval_every != 0:
            return

        fhr = self._fhr_window(ctx)
        bw = self._bandwidth_bpm(fhr)
        zc = self._zero_crossings_per_min(
            fhr, ctx.fs
        )  # ctx.fs = частота дискретизации FHR
        baseline10 = ctx.nc.last_notification.get(
            "median_fhr_10min"
        )  # уже поддерживается

        s_bas = self._score_baseline(baseline10)
        s_bw = self._score_bandwidth(bw)
        s_zc = self._score_zero_cross(zc)
        s_acc = self._score_accels(ctx)
        s_dec = self._score_decels(ctx)

        total = int(s_bas + s_bw + s_zc + s_acc + s_dec)
        if total >= 8:
            cat, color = "Нормальное", "green"
        elif total >= 5:
            cat, color = "Сомнительное", "yellow"
        else:
            cat, color = "Патологическое", "red"

        if ctx.nc.last_notification["fischer_score"] != total:
            ctx.nc.notify(ctx.now_t, f"Фишер: {total} баллов ({cat})", color=color)

        ctx.nc.last_notification["fischer_score"] = total
        ctx.nc.last_notification["fischer_category"] = cat


class StatusComposerStage:
    """Читает последние уведомления и составляет строку статуса."""

    def tick(self, ctx: StreamContext) -> None:
        proba = ctx.nc.last_notification.get(
            "hypoxia_proba_ewma"
        ) or ctx.nc.last_notification.get("hypoxia_proba")
        txt_proba = "недоступно" if proba is None else f"{round(proba*100):d}%"
        if proba is None:
            minutes_to_demonstrate = 9 - (ctx.now_t // 60)
            prefix = f"Вероятность гипоксии плода: будет доступно через {minutes_to_demonstrate} мин"
        elif proba >= 0.80:
            prefix = f"Высокая вероятность гипоксии плода: {txt_proba}"
        elif proba >= 0.50:
            prefix = f"Повышенная вероятность гипоксии плода: {txt_proba}"
        else:
            prefix = f"Вероятность гипоксии плода: {txt_proba}"

        notes = []
        # events
        active_accel = getattr(ctx, "active_accel", None)
        active_decel = getattr(ctx, "active_decel", None)

        if active_accel is not None:
            notes.append("Акцелерация")
        if active_decel is not None:
            notes.append("Децелерация")

        # tachy/brady
        if ctx.state_flags.get("tachy_active"):
            baseline = ctx.nc.last_notification.get("median_fhr_10min")
            curr = ctx.nc.last_notification.get("current_fhr")
            delta_txt = ""
            if baseline is not None and curr is not None:
                delta = curr - baseline
                if not np.isnan(delta):
                    sign = "+" if delta >= 0 else "−"
                    delta_txt = f" ({sign}{abs(round(delta))} bpm от базального ритма)"
            notes.append(f"Подозрение на тахикардию{delta_txt}")

        elif ctx.state_flags.get("brady_active"):
            notes.append("Подозрение на брадикардию")

        status = prefix if not notes else prefix + " | " + " | ".join(notes)
        ctx.nc.last_notification["current_status"] = status
