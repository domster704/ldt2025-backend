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
    """
    FIGO по таблице:
      - Базальный ритм: норма 110–150; препатология 100–110 или 150–170; патология <100 или >170
      - Вариабельность (амплитуда, уд/мин): норма 5–25; препатология 5–10 >40 мин или >25; патология <5 >40 мин или синусоидальный
      - Акцелерации (за 10 мин): норма ≥2/10 мин; препатология — отсутствуют >40 мин
      - Децелерации: норма — отсутствуют/спорадические неглубокие; препатология — спорадические любого типа;
                     патология — периодические выраженные поздние (>=2 late за 10 мин с амплитудой ≥15 bpm)
    """

    def __init__(self, variab_win_sec: int = 600, long_thr_sec: int = 40 * 60):
        self.variab_win_sec = variab_win_sec  # окно для оценки амплитуды (10 мин)
        self.long_thr_sec = long_thr_sec  # 40 минут
        # таймеры для длительных состояний вариабельности
        self._low_var_since: Optional[int] = None  # <5
        self._midlow_var_since: Optional[int] = None  # 5–10
        # отсутствие акцелераций
        self._no_accel_since: Optional[int] = 0

    # ---------- helpers ----------

    def _fhr_last(self, ctx: StreamContext, sec: int) -> Optional[np.ndarray]:
        vals = slice_last_seconds(ctx.sec_fhr, ctx.now_t, sec)
        x = np.array([v for v in vals if pd.notna(v)], dtype=float)
        return x if x.size else None

    def _amp_band(self, fhr: np.ndarray) -> float:
        # амплитуда как половина междецильного размаха (устойчиво к выбросам)
        p10, p90 = np.nanpercentile(fhr, 10), np.nanpercentile(fhr, 90)
        return float(max(0.0, (p90 - p10) / 2.0))

    def _sinusoidal_like(self, fhr: Optional[np.ndarray]) -> bool:
        # грубая эвристика: очень узкая полоса + регулярность
        if fhr is None or len(fhr) < 60:
            return False
        amp = self._amp_band(fhr)
        if (
            amp >= 5
        ):  # у синусоидального амплитуда обычно ~5–15, но вариабельность "монотонная".
            # попробуем проверить "монотонность": мало смен знака вокруг сглаженной линии
            trend = (
                pd.Series(fhr).rolling(15, min_periods=1, center=True).median().values
            )
            y = fhr - trend
            crossings = np.where(np.diff(np.signbit(y)))[0]
            per_min = len(fhr) / 5 / 60.0
            return (amp < 10) and (len(crossings) / max(1.0, per_min) <= 2.0)
        return amp < 5  # очень узкая — допустим как прокси к плохому паттерну

    def _accels_last(self, ctx: StreamContext, sec: int) -> int:
        lo = ctx.now_t - sec
        return sum(
            1
            for a in ctx.nc.last_notification["accelerations"]
            if a.get("start") is not None and a["start"] >= lo
        )

    def _last_accel_time(self, ctx: StreamContext) -> Optional[int]:
        acc = ctx.nc.last_notification["accelerations"]
        if not acc:
            return None
        # берём время конца, если есть, иначе старт
        return max(
            (a.get("end") if a.get("end") is not None else a["start"]) for a in acc
        )

    def _decels_last10(self, ctx: StreamContext) -> List[dict]:
        lo = ctx.now_t - 600
        return [
            d
            for d in ctx.nc.last_notification["decelerations"]
            if d.get("start") is not None and d["start"] >= lo
        ]

    # -------- per-parameter categories --------

    def _baseline_cat(self, baseline: Optional[float]) -> Tuple[str, Optional[str]]:
        if baseline is None:
            return "unknown", "Нет 10-мин базального"
        if baseline < 100 or baseline > 170:
            return "path", f"Базальный {baseline:.0f} уд/мин (<100 или >170)"
        if (100 <= baseline < 110) or (150 <= baseline <= 170):
            return "pre", f"Базальный {baseline:.0f} (100–110 или 150–170)"
        return "norm", None  # 110–150

    def _variability_cat(
        self, ctx: StreamContext, fhr10: Optional[np.ndarray]
    ) -> Tuple[str, Optional[str]]:
        if fhr10 is None or len(fhr10) < 5 * 60:  # <1 мин данных — мало для оценки
            return "unknown", "Недостаточно данных для вариабельности"
        amp = self._amp_band(fhr10)  # уд/мин
        now = ctx.now_t

        # обновляем таймеры длительности
        if amp < 5:
            self._low_var_since = self._low_var_since or now
            self._midlow_var_since = None
        elif 5 <= amp <= 10:
            self._midlow_var_since = self._midlow_var_since or now
            self._low_var_since = None
        else:
            self._low_var_since = None
            self._midlow_var_since = None

        # синусоидальный (патология)
        if self._sinusoidal_like(fhr10):
            return "path", "Синусоидальный ритм"

        # длительные состояния
        if (
            self._low_var_since is not None
            and (now - self._low_var_since) >= self.long_thr_sec
        ):
            return "path", f"Вариабельность <5 уд/мин >40 мин (≈{amp:.1f})"
        if amp > 25:
            return "pre", f"Вариабельность >25 уд/мин (≈{amp:.1f})"
        if (
            self._midlow_var_since is not None
            and (now - self._midlow_var_since) >= self.long_thr_sec
        ):
            return "pre", f"Вариабельность 5–10 уд/мин >40 мин (≈{amp:.1f})"
        # иначе в пределах нормы 5–25
        if 5 <= amp <= 25:
            return "norm", None
        # короткие отклонения трактуем как unknown/pre в зависимости от стороны
        return (
            "pre" if amp < 5 else "pre"
        ), f"Кратковременная вариабельность {'<5' if amp<5 else '>25'} (≈{amp:.1f})"

    def _accelerations_cat(self, ctx: StreamContext) -> Tuple[str, Optional[str]]:
        n10 = self._accels_last(ctx, 600)
        if n10 >= 2:
            self._no_accel_since = None
            return "norm", None
        last_acc = self._last_accel_time(ctx)
        if last_acc is None:
            # не было ни одной акцелерации с начала наблюдения
            none_for = ctx.now_t
        else:
            none_for = ctx.now_t - last_acc
        # запомним, откуда идёт «нет акцелераций»
        self._no_accel_since = self._no_accel_since or (ctx.now_t - none_for)
        if none_for >= self.long_thr_sec:
            return "pre", "Акцелерации отсутствуют >40 мин"
        # отсутствие в последние 10 минут — не делаем «патологию» по FIGO
        return "unknown", "Мало/нет акцелераций за 10 мин"

    def _decelerations_cat(self, ctx: StreamContext) -> Tuple[str, Optional[str]]:
        dec10 = self._decels_last10(ctx)
        if not dec10:
            return "norm", None
        # есть поздние выраженные периодические? (берём как ≥2 late с амплитудой ≥15 bpm за 10 мин)
        late_expr = [
            d for d in dec10 if d.get("type") == "late" and (d.get("amp_bpm", 0) >= 15)
        ]
        if len(late_expr) >= 2:
            return "path", "Периодические выраженные поздние децелерации"
        # иначе — спорадические любого типа => препатология
        # (нормой считаем «неглубокие спорадические»: ≤1 эпизод и amp<15, не late)
        if (
            len(dec10) == 1
            and dec10[0].get("amp_bpm", 0) < 15
            and dec10[0].get("type") != "late"
        ):
            return "norm", "Спорадическая неглубокая децелерация"
        return "pre", "Спорадические децелерации"

    def tick(self, ctx: StreamContext) -> None:

        if ctx.now_t % 60 != 0:
            return
        baseline = ctx.nc.last_notification.get(
            "median_fhr_10min"
        )  # ДОЛЖНО быть за 600с
        fhr10 = self._fhr_last(ctx, self.variab_win_sec)

        b_cat, b_reason = self._baseline_cat(baseline)
        v_cat, v_reason = self._variability_cat(ctx, fhr10)
        a_cat, a_reason = self._accelerations_cat(ctx)
        d_cat, d_reason = self._decelerations_cat(ctx)

        # финальная агрегация по FIGO
        reasons = []
        cats = [
            ("baseline", b_cat, b_reason),
            ("variability", v_cat, v_reason),
            ("accelerations", a_cat, a_reason),
            ("decelerations", d_cat, d_reason),
        ]

        n_path = sum(1 for _, c, _ in cats if c == "path")
        n_pre = sum(1 for _, c, _ in cats if c == "pre")

        if n_path >= 1:
            status, color = "Патологическое", "red"
        elif n_pre >= 1:
            status, color = "Сомнительное", "yellow"
        else:
            # если всё norm/unknown и нет достаточных данных — считаем «Препатология» (сомнительное)
            if any(c == "unknown" for _, c, _ in cats):
                status, color = "Сомнительное", "yellow"
            else:
                status, color = "Нормальное", "green"

        for name, c, r in cats:
            if (c in ("pre", "path")) and r:
                reasons.append(r)
        note = f"FIGO: {status}"
        if reasons:
            note += " — " + "; ".join(reasons[:3])  # до 3 причин, чтобы не шуметь

        prev = ctx.state_flags.get("figo_last")
        ctx.nc.last_notification["figo_situation"] = status
        if status != prev:
            ctx.nc.notify(ctx.now_t, note, color=color)
            ctx.state_flags["figo_last"] = status


class ContractionStage:
    """
    Онлайновая детекция схваток по UC с робастным базисом и динамическим порогом.
    - Базис: медиана за baseline_win.
    - Порог: max(amp_thr_abs, iqr*iqr_k).
    - Сглаживание: медианная фильтрация коротким окном.
    """

    def __init__(
        self,
        baseline_win=180,
        amp_thr_abs=12.0,
        iqr_k=0.9,
        min_len=25,
        cooldown=10,
        smooth_win=5,
    ):
        self.baseline_win = baseline_win
        self.amp_thr_abs = amp_thr_abs
        self.iqr_k = iqr_k
        self.min_len = min_len
        self.cooldown = cooldown
        self.smooth_win = smooth_win
        self.active = None
        self.last_end = -(10**9)

    def _median_last(self, arr, now, sec):
        return median_last_seconds(arr, now, sec)

    def _iqr_last(self, arr, now, sec):
        vals = slice_last_seconds(arr, now, sec)
        if not vals:
            return None
        x = np.array([v for v in vals if pd.notna(v)], dtype=float)
        return float(np.subtract(*np.nanpercentile(x, [75, 25]))) if x.size else None

    def tick(self, ctx: StreamContext) -> None:
        if not ctx.sec_uc or ctx.sec_uc[-1][0] != ctx.now_t:
            return
        now = ctx.now_t
        uc = ctx.sec_uc[-1][1]
        if pd.isna(uc):
            return

        # сглаживание медианным окном по последним smooth_win секундам
        vals = slice_last_seconds(ctx.sec_uc, now, self.smooth_win)
        if not vals:
            return
        uc_smooth = float(np.median(vals)) if len(vals) else uc

        base = self._median_last(ctx.sec_uc, now, self.baseline_win)
        iqr = self._iqr_last(ctx.sec_uc, now, self.baseline_win)
        if base is None or iqr is None:
            return

        thr_dyn = max(self.amp_thr_abs, iqr * self.iqr_k)
        above = (uc_smooth - base) >= thr_dyn

        if self.active is None:
            if above and (now - self.last_end) >= self.cooldown:
                self.active = {
                    "start": now,
                    "peak": now,
                    "peak_value": uc_smooth,
                    "base": base,
                    "thr": thr_dyn,
                }
                ctx.nc.notify(
                    now, f"Старт схватки (UC↑ ≥ {thr_dyn:.1f})", color="yellow"
                )
        else:
            # обновляем пик
            if uc_smooth > self.active["peak_value"]:
                self.active["peak_value"] = uc_smooth
                self.active["peak"] = now
            # завершение
            if not above:
                dur = now - self.active["start"]
                if dur >= self.min_len:
                    self.active["end"] = now
                    amp = float(self.active["peak_value"] - self.active["base"])
                    self.active["amp"] = float(round(amp, 1))
                    ctx.nc.last_notification["contractions"].append(self.active)
                    ctx.nc.notify(
                        now,
                        f"Схватка: amp≈{self.active['amp']} UC, {dur}s",
                        color="yellow",
                    )
                    self.last_end = now
                self.active = None


class AdvancedAccelDecelStage:
    """
    Адаптивная детекция акцелераций/децелераций:
    - Робастный локальный базис (медиана по win).
    - Порог: max(fixed_thr, iqr*k_z) по Δbpm.
    - Разрешаем короткие разрывы до gap_tol_sec.
    - Доп. критерий площади (AUC) в bpm*sec для длинных слабых эпизодов.
    - Классификация децелераций по привязке к схваткам улучшена.
    """

    def __init__(
        self,
        local_baseline_window_sec=90,
        accel_fixed_thr=12.0,
        decel_fixed_thr=-12.0,
        iqr_k=0.85,
        min_len=10,
        gap_tol_sec=3,
        area_thr_accel=120.0,  # ~10 bpm * 12 s
        area_thr_decel=120.0,
    ):
        self.win = local_baseline_window_sec
        self.accel_fixed_thr = accel_fixed_thr
        self.decel_fixed_thr = decel_fixed_thr
        self.iqr_k = iqr_k
        self.min_len = min_len
        self.gap_tol = gap_tol_sec
        self.area_thr_accel = area_thr_accel
        self.area_thr_decel = area_thr_decel

        self.accel_active = None
        self.decel_active = None
        self._accel_gap = 0
        self._decel_gap = 0

    def _robust_base_iqr(self, arr, now, sec):
        vals = slice_last_seconds(arr, now, sec)
        if not vals:
            return None, None
        x = np.array([v for v in vals if pd.notna(v)], dtype=float)
        if x.size == 0:
            return None, None
        base = float(np.nanmedian(x))
        iqr = float(np.subtract(*np.nanpercentile(x, [75, 25])))
        return base, iqr

    def _nearest_contraction(self, ctx: StreamContext, t0: int, t1: int):
        overlaps = []
        for c in ctx.nc.last_notification["contractions"]:
            if c.get("end") is not None and c["end"] >= t0 and c["start"] <= t1:
                overlaps.append(c)
        return (
            max(overlaps, key=lambda c: min(t1, c["end"]) - max(t0, c["start"]))
            if overlaps
            else None
        )

    def _classify_decel(self, ctx: StreamContext, start: int, end: int, amp: float):
        c = self._nearest_contraction(ctx, start, end)
        if c is None:
            return "variable", None, None
        lag_start = start - c["start"]
        # поздняя: начало спустя ≥30с от старта схватки и возврат после конца схватки
        if lag_start >= 30 and end >= c["end"]:
            grade = "mild" if amp <= 15 else "moderate" if amp <= 45 else "severe"
            return (
                "late",
                grade,
                {"contraction_start": c["start"], "contraction_peak": c["peak"]},
            )
        # ранняя: примерно синхронна со схваткой
        if abs(lag_start) <= 10 and c["start"] <= start <= c["peak"] <= end <= c["end"]:
            return (
                "early",
                None,
                {"contraction_start": c["start"], "contraction_peak": c["peak"]},
            )
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

        base, iqr = self._robust_base_iqr(ctx.sec_fhr, now, self.win)
        if base is None or iqr is None:
            return
        delta = float(curr - base)

        # адаптивные пороги
        accel_thr = max(self.accel_fixed_thr, iqr * self.iqr_k)
        decel_thr = min(self.decel_fixed_thr, -iqr * self.iqr_k)  # отрицательный

        # ===== АКЦЕЛЕРАЦИИ =====
        if delta >= accel_thr:
            if self.accel_active is None:
                self.accel_active = {"start": now, "peak": curr, "amp": 0.0, "auc": 0.0}
                self._accel_gap = 0
                ctx.nc.notify(
                    now, f"Старт акцелерации (Δ≥{accel_thr:.1f} bpm)", color="yellow"
                )
            else:
                if curr > self.accel_active["peak"]:
                    self.accel_active["peak"] = curr
            self.accel_active["amp"] = max(self.accel_active["amp"], delta)
            self.accel_active["auc"] += max(0.0, delta)
            ctx.active_accel = self.accel_active
        else:
            # допустим короткий разрыв
            if self.accel_active is not None:
                self._accel_gap += 1
                if self._accel_gap <= self.gap_tol:
                    # продолжаем копить площадь даже на грани порога (если чуть ниже — 0)
                    pass
                else:
                    # закрытие
                    dur = now - self.accel_active["start"] - self._accel_gap + 1
                    if (
                        dur >= self.min_len
                        or self.accel_active["auc"] >= self.area_thr_accel
                    ):
                        amp = float(round(self.accel_active["amp"], 1))
                        end_t = now - self._accel_gap
                        ctx.nc.last_notification["accelerations"].append(
                            {
                                "start": self.accel_active["start"],
                                "end": end_t,
                                "amp_bpm": amp,
                                "dur_s": int(dur),
                            }
                        )
                        ctx.nc.notify(
                            end_t, f"Акцелерация: +{amp} bpm, {dur}s", color="yellow"
                        )
                    self.accel_active = None
                    ctx.active_accel = None
                    self._accel_gap = 0

        # ===== ДЕЦЕЛЕРАЦИИ =====
        if delta <= decel_thr:
            if self.decel_active is None:
                self.decel_active = {
                    "start": now,
                    "nadir": curr,
                    "amp": 0.0,
                    "auc": 0.0,
                }
                self._decel_gap = 0
                ctx.nc.notify(
                    now, f"Старт децелерации (Δ≤{decel_thr:.1f} bpm)", color="yellow"
                )
            else:
                if curr < self.decel_active["nadir"]:
                    self.decel_active["nadir"] = curr
            self.decel_active["amp"] = min(
                self.decel_active["amp"], delta
            )  # отрицательная
            self.decel_active["auc"] += max(0.0, -delta)
            ctx.active_decel = self.decel_active
        else:
            if self.decel_active is not None:
                self._decel_gap += 1
                if self._decel_gap <= self.gap_tol:
                    pass
                else:
                    dur = now - self.decel_active["start"] - self._decel_gap + 1
                    if (
                        dur >= self.min_len
                        or self.decel_active["auc"] >= self.area_thr_decel
                    ):
                        amp = float(round(abs(self.decel_active["amp"]), 1))
                        end_t = now - self._decel_gap
                        dec_type, grade, uc_ref = self._classify_decel(
                            ctx, self.decel_active["start"], end_t, amp
                        )
                        ctx.nc.last_notification["decelerations"].append(
                            {
                                "start": self.decel_active["start"],
                                "end": end_t,
                                "amp_bpm": amp,
                                "dur_s": int(dur),
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
                            end_t,
                            label,
                            color="yellow" if dec_type != "late" else "red",
                        )
                    self.decel_active = None
                    ctx.active_decel = None
                    self._decel_gap = 0

        # обновим счетчики
        ctx.nc.last_notification["accelerations_count"] = len(
            ctx.nc.last_notification["accelerations"]
        )
        ctx.nc.last_notification["decelerations_count"] = len(
            ctx.nc.last_notification["decelerations"]
        )


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
        if all(d.get_id() == "early" for d in recent):
            return 2
        # если есть поздние краткие/вариабельные → 1
        # считаем «краткой» < 60 с
        if any(
                (d.get_id() in ("late", "variable")) and d.get_id() < 60
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
        if any(d.get_id() == "late" for d in recent):
            return 0
        if any(d.get_id() == "early" for d in recent):
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
        baseline10 = ctx.nc.last_notification.get_id()  # уже поддерживается

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
    """Расширенный статус для быстрого чтения."""

    def tick(self, ctx: StreamContext) -> None:
        proba = ctx.nc.last_notification.get(
            "hypoxia_proba_ewma"
        ) or ctx.nc.last_notification.get("hypoxia_proba")
        txt_proba = "недоступно" if proba is None else f"{round(proba*100):d}%"
        if proba is None:
            minutes_to_demonstrate = max(0, 9 - (ctx.now_t // 60))
            prefix = f"Вероятность гипоксии плода: будет доступно через {minutes_to_demonstrate} мин"
        elif proba >= 0.80:
            prefix = f"Высокая вероятность гипоксии плода: {txt_proba}"
        elif proba >= 0.50:
            prefix = f"Повышенная вероятность гипоксии плода: {txt_proba}"
        else:
            prefix = f"Вероятность гипоксии плода: {txt_proba}"

        notes = []
        ln = ctx.nc.last_notification

        # активные события
        if getattr(ctx, "active_accel", None) is not None:
            notes.append("Акцелерация (идёт)")
        if getattr(ctx, "active_decel", None) is not None:
            notes.append("Децелерация (идёт)")

        # tachy/brady
        if ctx.state_flags.get("tachy_active"):
            baseline = ln.get("median_fhr_10min")
            curr = ln.get("current_fhr")
            if baseline is not None and curr is not None:
                delta = curr - baseline
                sign = "+" if delta >= 0 else "−"
                notes.append(
                    f"Подозрение на тахикардию ({sign}{abs(round(delta))} bpm от базального)"
                )
            else:
                notes.append("Подозрение на тахикардию")
        elif ctx.state_flags.get("brady_active"):
            notes.append("Подозрение на брадикардию")

        # краткие числовые подсказки
        if (
            ln.get("accelerations_count") is not None
            and ln.get("decelerations_count") is not None
        ):
            notes.append(
                f"Акцел/Децел: {ln['accelerations_count']}/{ln['decelerations_count']}"
            )

        status = prefix if not notes else prefix + " | " + " | ".join(notes)
        ctx.nc.last_notification["current_status"] = status
