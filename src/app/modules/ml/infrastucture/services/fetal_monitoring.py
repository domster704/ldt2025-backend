from collections import deque

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from app.modules.ml.application.interfaces.fetal_monitoring import IFetalMonitoring
from app.modules.ml.domain.entities.process import Process, ProcessResults, TimeRange


class FetalMonitoringService(IFetalMonitoring):
    """
    Реал-тайм сервис для анализа FHR (value_bpm) и UC (value_uterus) со стримового ввода.
    Предполагается, что process_stream вызывается раз в секунду и ему передают df
    с новыми строками (или всем df — он сам отфильтрует до текущей секунды).
    """

    def __init__(self, model_hypoxia_config, model_stv_config):
        self.model_hypoxia_config = model_hypoxia_config
        self.model_stv_config = model_stv_config

        self.fs = self.model_hypoxia_config["fs"]

        self.streaming_last_second = 0
        self.current_df = None

        # Пороговая логика
        self.tachycardia_seconds_threshold = 10
        self.tachycardia_bpm_threshold = 160
        self.bradycardia_bpm_threshold = 110
        self.bradycardia_seconds_threshold = 10

        # Настройки событий акцелераций/децелераций
        self.accel_delta_bpm = 15
        self.decel_delta_bpm = -15
        self.min_event_duration_sec = 15
        self.local_baseline_window_sec = 60  # для локального базиса

        # Истории посекундных средних для онлайна
        self.sec_fhr = deque(maxlen=30 * self.fs * 60)
        self.sec_uc = deque(maxlen=30 * self.fs * 60)

        # Состояния текущих (активных) эпизодов
        self.active_accel = None
        self.active_decel = None

        # Прогнозы для STV
        self.stv_forecast = None

        # Накопительные уведомления
        self.notifications = {}

        # EWMA для гипоксии
        self.hypoxia_ewma_alpha = 0.01
        self._hypoxia_proba_ewma = None

        # Последние состояния
        self._state_flags = {
            "tachy_active": False,
            "brady_active": False,
            "hypoxia_active": False,
            "figo_last": None,
        }

        self.last_notification = {
            "tachycardia": "Недостаточно данных",
            "hypoxia_proba": None,
            # 1) Акцелерации/децелерации — список словарей {'start': t0, 'end': t1 или None}
            "accelerations": [],
            "decelerations": [],
            # 2) Медианный ЧСС за 10 минут (базальная)
            "median_fhr_10min": None,
            # 3) Текущий ЧСС и 4) текущий uterus (посекундные средние)
            "current_fhr": None,
            "current_uterus": None,
            # 5) STV (последние 10 минут, Dawes–Redman-подобный)
            "stv": None,
            # 6) Прогнозы для STV
            "stv_forecast": None,
            # 7) Текущая ситуация по FIGO
            "figo_situation": None,
            # 8) Накопленные уведомления
            "notifications": {},
            # 9) Текущий статус
            "current_status": None,
            # 10) Время в секундах
            "time_sec": 0,
        }

    # ====== Внутренние утилиты ======

    def _notify(self, now_t: int, message: str, color: str = "yellow"):
        if now_t not in self.notifications:
            self.notifications[now_t] = []
            self.notifications[now_t].append({"message": message, "color": color})
        # Не добавляем дубли в ту же секунду
        if message not in self.notifications[now_t]:
            self.notifications[now_t].append({"message": message, "color": color})

    def _slice_last_seconds(self, deq, now_t, seconds):
        lo = now_t - seconds + 1
        vals = [v for (t, v) in deq if t >= lo and t <= now_t and pd.notna(v)]
        return vals

    def _slice_last_seconds_numpy(self, arr, seconds):
        n = len(arr)
        need = int(seconds * self.fs)
        if n <= 0:
            return np.array([])
        start = max(0, n - need)
        return arr[start:n]

    def _median_last_seconds(self, deq, now_t, seconds):
        vals = self._slice_last_seconds(deq, now_t, seconds)
        return float(np.median(vals)) if len(vals) > 0 else None

    def _baseline_10min(self, now_t):
        return self._median_last_seconds(self.sec_fhr, now_t, 600)

    def stv_dawes_redman(self, fhr: np.ndarray) -> float:
        """
        Делим ряд длиной N минут на 16*N подпериодов (почти равных),
        считаем среднее в каждом подпериоде, затем mean(|diff|) между соседними средними.
        """
        if fhr is None or len(fhr) == 0:
            return np.nan

        minutes = len(fhr) // (self.fs * 60)
        if minutes <= 0:
            return np.nan

        chunks = np.array_split(fhr, 16 * minutes)
        means = np.array([np.nanmean(c) if len(c) else np.nan for c in chunks])
        if len(means) < 2:
            return np.nan
        diffs = np.abs(np.diff(means))
        return float(np.nanmean(diffs))

    def _second_mean(self, df, end_second):
        """Средние FHR и UC на интервале (end_second-1, end_second]. Если нет данных — np.nan."""
        start = end_second - 1
        sl = df[(df["time_sec"] > start) & (df["time_sec"] <= end_second)]
        return sl["value_bpm"].mean(), sl["value_uterus"].mean()

    # ====== Модель ======

    def _update_hypoxia_ewma(self, proba: float):
        if proba is None or (isinstance(proba, float) and np.isnan(proba)):
            return
        if self._hypoxia_proba_ewma is None:
            self._hypoxia_proba_ewma = float(proba)
        else:
            a = self.hypoxia_ewma_alpha
            self._hypoxia_proba_ewma = float(
                a * proba + (1 - a) * self._hypoxia_proba_ewma
            )

        return round(self._hypoxia_proba_ewma, 3)

    def create_window(self, df):
        df_temp = df[
            (
                df["time_sec"]
                >= self.streaming_last_second - self.model_stv_config["window_size"]
            )
            & (df["time_sec"] <= self.streaming_last_second)
        ].copy()
        df_temp["window_time_max"] = self.streaming_last_second
        return df_temp

    @property
    def features(self):
        return [
            "median_uc",
            "mean_uc",
            "std_uc",
            "min_uc",
            "max_uc",
            "median_fhr",
            "mean_fhr",
            "std_fhr",
            "min_fhr",
            "max_fhr",
            "sdnn",
            "rmssd",
            "pnn50",
            "uc_corr",
            "window_time_max",
        ]

    def extract_features(self, window_df):
        if window_df.empty:
            return {**{f: np.nan for f in self.features}}

        fhr = window_df["value_bpm"].astype(float).values
        uc = window_df["value_uterus"].astype(float).values
        window_time = window_df["window_time_max"].values[0]

        rr_diff = np.diff(fhr)
        sdnn = np.std(fhr) if len(fhr) else np.nan
        rmssd = np.sqrt(np.mean(rr_diff**2)) if len(rr_diff) > 0 else np.nan
        pnn50 = (
            np.mean(np.abs(rr_diff) > 50) if len(rr_diff) > 0 else np.nan
        )  # упрощенно

        median_fhr = np.median(fhr) if len(fhr) else np.nan
        mean_fhr = np.mean(fhr) if len(fhr) else np.nan
        std_fhr = np.std(fhr) if len(fhr) else np.nan
        min_fhr = np.min(fhr) if len(fhr) else np.nan
        max_fhr = np.max(fhr) if len(fhr) else np.nan

        median_uc = np.median(uc) if len(uc) else np.nan
        mean_uc = np.mean(uc) if len(uc) else np.nan
        std_uc = np.std(uc) if len(uc) else np.nan
        min_uc = np.min(uc) if len(uc) else np.nan
        max_uc = np.max(uc) if len(uc) else np.nan

        corr = (
            np.corrcoef(fhr, uc)[0, 1]
            if (len(fhr) > 1 and np.std(uc) > 0 and np.std(fhr) > 0)
            else np.nan
        )

        return {
            "median_uc": median_uc,
            "mean_uc": mean_uc,
            "std_uc": std_uc,
            "min_uc": min_uc,
            "max_uc": max_uc,
            "median_fhr": median_fhr,
            "mean_fhr": mean_fhr,
            "std_fhr": std_fhr,
            "min_fhr": min_fhr,
            "max_fhr": max_fhr,
            "sdnn": sdnn,
            "rmssd": rmssd,
            "pnn50": pnn50,
            "uc_corr": corr,
            "window_time_max": window_time,
        }

    # ====== Уведомления ======

    def _compose_current_status(self, now_t: int):
        """
        Формирует компактную строку статуса.
        Основа: вероятность гипоксии.
        Далее: пометки об отклонениях — акцелерация/децелерация/тахикардия.
        """
        proba = self.last_notification.get("hypoxia_proba_ewma")
        if proba is None:
            proba = self.last_notification.get("hypoxia_proba")
        txt_proba = "недоступно" if proba is None else f"{round(proba*100):d}%"

        if proba is None:
            prefix = "Вероятность гипоксии плода: недоступно"
        elif proba >= 0.80:
            prefix = f"Высокая вероятность гипоксии плода: {txt_proba}"
        elif proba >= 0.50:
            prefix = f"Повышенная вероятность гипоксии плода: {txt_proba}"
        else:
            prefix = f"Вероятность гипоксии плода: {txt_proba}"

        notes = []

        if self.active_accel is not None and self.active_accel.get("announced"):
            notes.append("Акцелерация (≥15с)")
        if self.active_decel is not None and self.active_decel.get("announced"):
            notes.append("Децелерация (≥15с)")

        if self._state_flags.get("tachy_active"):
            baseline = self.last_notification.get("median_fhr_10min")
            curr = self.last_notification.get("current_fhr")
            delta_txt = ""
            if baseline is not None and curr is not None:
                delta = curr - baseline
                if not np.isnan(delta):
                    sign = "+" if delta >= 0 else "−"
                    delta_txt = f" ({sign}{abs(round(delta))} bpm от базального ритма)"
            notes.append(f"Подозрение на тахикардию{delta_txt}")

        if self._state_flags.get("brady_active"):
            notes.append("Подозрение на брадикардию")

        status = prefix if not notes else prefix + " | " + " | ".join(notes)
        self.last_notification["current_status"] = status

    def _update_tachycardia(self, now_t):
        if now_t % self.tachycardia_seconds_threshold != 0:
            return

        median_10 = self._baseline_10min(now_t)
        self.last_notification["median_fhr_10min"] = median_10

        if median_10 is None:
            self.last_notification["tachycardia"] = "Недостаточно данных"
            self._state_flags["tachy_active"] = False
            return

        if median_10 > self.tachycardia_bpm_threshold:
            deviation = round(median_10 - self.tachycardia_bpm_threshold, 1)
            self.last_notification["tachycardia"] = (
                f"Подозрение на тахикардию (базальная ≈ {median_10:.1f} bpm, +{deviation} bpm)."
            )
            if not self._state_flags["tachy_active"]:
                self._notify(
                    now_t, f"Тахикардия: базальная ≈ {median_10:.1f} bpm", color="red"
                )
                self._state_flags["tachy_active"] = True
        else:
            self.last_notification["tachycardia"] = (
                f"Нет признаков тахикардии (базальная ≈ {median_10:.1f} bpm)."
            )
            if self._state_flags["tachy_active"]:
                self._notify(now_t, "Тахикардия прекратилась", color="green")
            self._state_flags["tachy_active"] = False

    def _update_bradycardia(self, now_t):
        """Оценка брадикардии по базалу 10 мин, обновление каждые self.bradycardia_seconds_threshold сек."""
        if now_t % self.bradycardia_seconds_threshold != 0:
            return

        median_10 = self.last_notification["median_fhr_10min"]
        if median_10 is None:
            return

        if median_10 < self.bradycardia_bpm_threshold:
            if not self._state_flags["brady_active"]:
                self._notify(
                    now_t, f"Брадикардия: базальная ≈ {median_10:.1f} bpm", color="red"
                )
                self._state_flags["brady_active"] = True
        else:
            if self._state_flags["brady_active"]:
                self._notify(now_t, "Брадикардия прекратилась", color="green")
            self._state_flags["brady_active"] = False

    def _update_stv(self, now_t):
        """STV по последним 10 минутам — раз в 10 секунд."""
        if now_t % 10 != 0:
            return
        if self.current_df is None or self.current_df.empty:
            self.last_notification["stv"] = None
            return
        last_10_min_fhr = self._slice_last_seconds_numpy(
            self.current_df["value_bpm"].values, 600
        )
        stv = self.stv_dawes_redman(last_10_min_fhr)
        self.last_notification["stv"] = (
            None if stv is None or np.isnan(stv) else float(round(stv, 2))
        )

    def _update_accel_decel(self, now_t):
        """
        Детекция акцелераций/децелераций относительно локального базиса (медиана 60 с).
        - событие формируется при длительности >= self.min_event_duration_sec
        - в notifications отправляем только START/END
        """
        if not self.sec_fhr or self.sec_fhr[-1][0] != now_t:
            return

        curr_fhr = self.sec_fhr[-1][1]
        if pd.isna(curr_fhr):
            return

        baseline = self._median_last_seconds(
            self.sec_fhr, now_t, self.local_baseline_window_sec
        )
        if baseline is None:
            return

        delta = curr_fhr - baseline

        # --- Акцелерации ---
        if delta >= self.accel_delta_bpm and self.active_decel is None:
            if self.active_accel is None:
                self.active_accel = {
                    "start": now_t,
                    "count": 1,
                    "announced": False,
                    "list_idx": None,
                }
            else:
                self.active_accel["count"] += 1

            if (not self.active_accel["announced"]) and self.active_accel[
                "count"
            ] >= self.min_event_duration_sec:
                self.last_notification["accelerations"].append(
                    {"start": self.active_accel["start"], "end": None}
                )
                self.active_accel["list_idx"] = (
                    len(self.last_notification["accelerations"]) - 1
                )
                self.active_accel["announced"] = True
                self._notify(
                    self.active_accel["start"],
                    f"Началась акцелерация (≥{self.accel_delta_bpm} bpm от базиса)",
                    color="yellow",
                )
        else:
            if self.active_accel is not None:
                if (
                    self.active_accel["announced"]
                    and self.active_accel["list_idx"] is not None
                ):
                    idx = self.active_accel["list_idx"]
                    if self.last_notification["accelerations"][idx]["end"] is None:
                        self.last_notification["accelerations"][idx]["end"] = now_t - 1
                        self._notify(
                            now_t - 1, "Акцелерация завершилась", color="green"
                        )
                self.active_accel = None

        # --- Децелерации ---
        if delta <= self.decel_delta_bpm and self.active_accel is None:
            if self.active_decel is None:
                self.active_decel = {
                    "start": now_t,
                    "count": 1,
                    "announced": False,
                    "list_idx": None,
                }
            else:
                self.active_decel["count"] += 1

            if (not self.active_decel["announced"]) and self.active_decel[
                "count"
            ] >= self.min_event_duration_sec:
                self.last_notification["decelerations"].append(
                    {"start": self.active_decel["start"], "end": None}
                )
                self.active_decel["list_idx"] = (
                    len(self.last_notification["decelerations"]) - 1
                )
                self.active_decel["announced"] = True
                self._notify(
                    self.active_decel["start"],
                    f"Началась децелерация (≤{self.decel_delta_bpm} bpm от базиса)",
                    color="yellow",
                )
        else:
            if self.active_decel is not None:
                if (
                    self.active_decel["announced"]
                    and self.active_decel["list_idx"] is not None
                ):
                    idx = self.active_decel["list_idx"]
                    if self.last_notification["decelerations"][idx]["end"] is None:
                        self.last_notification["decelerations"][idx]["end"] = now_t - 1
                        self._notify(
                            now_t - 1, "Децелерация завершилась", color="green"
                        )
                self.active_decel = None

    # ====== FIGO (упрощённые правила) ======
    def _update_figo(self, now_t):
        """
        Правила
          - Preterminal: базал < 100 bpm ИЛИ STV < 1.0
          - Pathological: базал > 180 ИЛИ (160–180 и STV < 2.0) ИЛИ есть длительная децелерация > 3 мин
          - Suspicious: 100–109 ИЛИ 161–180 ИЛИ STV 1–2.9 ИЛИ частые децелерации
          - Normal: 110–160 и STV ≥ 3 и нет децелераций ≥ 15 с за последние 10 мин
        """
        baseline = self.last_notification["median_fhr_10min"]
        stv_10 = self.last_notification["stv"]
        status = None

        # длительные децелерации > 3 мин среди закрытых за всю запись
        long_decels = any(
            (d["end"] is not None and (d["end"] - d["start"] + 1) >= 180)
            for d in self.last_notification["decelerations"]
        )
        # есть ли децелерации за последние 10 мин
        recent_decels = any(
            (d["end"] or now_t) >= now_t - 600 and (d["start"]) >= now_t - 600
            for d in self.last_notification["decelerations"]
        )

        if baseline is None or stv_10 is None:
            status = "Сомнительное"
            color = "yellow"
        else:
            if baseline < 100 or stv_10 < 1.0:
                status = "Претерминальное"
                color = "purple"
            elif (
                baseline > 180
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

        self.last_notification["figo_situation"] = status
        if status != self._state_flags["figo_last"]:
            self._notify(now_t, f"Состояние FIGO: {status}", color=color)
            self._state_flags["figo_last"] = status

    # ====== Главный метод стриминга ======

    def process_stream(self, df) -> Process | None:
        self.streaming_last_second += 1
        now_t = self.streaming_last_second

        self.current_df = df[df["time_sec"] <= now_t].copy()

        # Посекундные средние (текущие значения за последнюю секунду)
        curr_fhr, curr_uc = (np.nan, np.nan)
        if self.current_df is not None and not self.current_df.empty:
            curr_fhr, curr_uc = self._second_mean(self.current_df, now_t)

        self.sec_fhr.append((now_t, float(curr_fhr) if pd.notna(curr_fhr) else np.nan))
        self.sec_uc.append((now_t, float(curr_uc) if pd.notna(curr_uc) else np.nan))

        # 3) текущий FHR & 4) текущий UC (посекундные средние)
        self.last_notification["current_fhr"] = (
            None if pd.isna(curr_fhr) else float(round(curr_fhr, 2))
        )
        self.last_notification["current_uterus"] = (
            None if pd.isna(curr_uc) else float(round(curr_uc, 2))
        )

        # Модели (STV forecast и hypoxia proba)
        model_stv_forecasts = {"stv_3m": None, "stv_5m": None, "stv_10m": None}
        if now_t % self.model_stv_config["step_size"] == 0:
            if now_t >= self.model_stv_config["window_size"]:
                window_df = self.create_window(self.current_df)
                features = self.extract_features(window_df)
                model_input = pd.DataFrame([features])

                for model_name, model in self.model_stv_config["models"].items():
                    model_result = model["model"].predict(model_input).item()
                    model_stv_forecasts[model_name] = model_result

                model_hypoxia_proba = (
                    self.model_hypoxia_config["model"]
                    .predict_proba(model_input)[:, 1]
                    .item()
                )
                model_hypoxia_proba = self._update_hypoxia_ewma(model_hypoxia_proba)
                self.last_notification["hypoxia_proba"] = model_hypoxia_proba
                self.last_notification["stv_forecast"] = model_stv_forecasts
                # оповещение при резком росте риска (пример порога)
                if model_hypoxia_proba >= 0.8:
                    if not self._state_flags["hypoxia_active"]:
                        self._notify(
                            now_t,
                            f"Высокая вероятность гипоксии: {model_hypoxia_proba:.2f}",
                            color="red",
                        )
                        self._state_flags["hypoxia_active"] = True
                else:
                    if self._state_flags["hypoxia_active"]:
                        self._notify(
                            now_t, "Вероятность гипоксии снизилась", color="green"
                        )
                    self._state_flags["hypoxia_active"] = False

        # 2) Базал 10 мин + тахи/бради (каждые X сек)
        self._update_tachycardia(now_t)
        self._update_bradycardia(now_t)

        # 5) STV 10 мин (каждые 10 сек)
        self._update_stv(now_t)

        # Акцелерации/децелерации
        self._update_accel_decel(now_t)

        # FIGO
        self._update_figo(now_t)

        self.last_notification["notifications"] = self.notifications
        self.last_notification["time_sec"] = now_t

        return Process(
            time_sec=now_t,
            current_status=self.last_notification["current_status"],
            notifications=self.notifications,
            figo_situation=self.last_notification["figo_situation"],
            current_fhr=self.last_notification["current_fhr"],
            current_uterus=self.last_notification["current_uterus"],
            stv=self.last_notification["stv"],
            stv_forecast=self.last_notification["stv_forecast"],
            median_fhr_10min=self.last_notification["median_fhr_10min"],
            hypoxia_proba=self.last_notification["hypoxia_proba"],
        )

    # ====== Итоги обследования ======

    def _rolling_stv_mean_10min(self, fhr: np.ndarray) -> float:
        """Среднее STV по всем полным 10-мин окнам записи (шаг 60 с)."""
        if fhr is None or len(fhr) < self.fs * 600:
            return np.nan
        win = self.fs * 600
        step = self.fs * 60
        stvs = []
        for start in range(0, len(fhr) - win + 1, step):
            stv = self.stv_dawes_redman(fhr[start : start + win])
            if not np.isnan(stv):
                stvs.append(stv)
        return float(np.nanmean(stvs)) if stvs else np.nan

    def finalize_process(self) -> ProcessResults:
        if self.current_df is None or self.current_df.empty:

            return ProcessResults(
                last_figo=None,
                baseline_bpm=None,
                stv_all=None,
                stv_10min_mean=None,
                accelerations_count=0,
                decelerations_count=0,
                uterus_mean=None,
            )
        # Последнее FIGO уже поддерживается онлайном
        last_figo = self.last_notification.get("figo_situation")

        # Базальная ЧСС (конец записи, 10 мин окно)
        baseline_bpm = self._baseline_10min(self.streaming_last_second)

        # STV по всей записи
        fhr_all = self.current_df["value_bpm"].astype(float).values
        stv_all = self.stv_dawes_redman(fhr_all)
        stv_all = None if np.isnan(stv_all) else float(round(stv_all, 2))

        # Средний STV по 10-мин окнам
        stv_10min_mean = self._rolling_stv_mean_10min(fhr_all)
        stv_10min_mean = (
            None if np.isnan(stv_10min_mean) else float(round(stv_10min_mean, 2))
        )

        # Количество событий
        accelerations_count = sum(
            1 for a in self.last_notification["accelerations"] if a["start"] is not None
        )
        decelerations_count = sum(
            1 for d in self.last_notification["decelerations"] if d["start"] is not None
        )

        # Среднее UC
        uterus_mean = (
            float(self.current_df["value_uterus"].astype(float).mean())
            if not self.current_df["value_uterus"].empty
            else None
        )
        if pd.isna(uterus_mean):
            uterus_mean = None
        else:
            uterus_mean = float(round(uterus_mean, 2))

        return ProcessResults(
            last_figo=last_figo,
            baseline_bpm=(
                None if baseline_bpm is None else float(round(baseline_bpm, 1))
            ),
            stv_all=stv_all,
            stv_10min_mean=stv_10min_mean,
            accelerations_count=int(accelerations_count),
            decelerations_count=int(decelerations_count),
            uterus_mean=uterus_mean,
        )

    @staticmethod
    def analyze_patient_dynamics(df: pd.DataFrame) -> str:
        notes = []

        last_baseline = df["baseline_bpm"].iloc[-1]
        if last_baseline > 160:
            notes.append("Повышенная базальная ЧСС (тахикардия)")
        elif last_baseline < 110:
            notes.append("Пониженная базальная ЧСС (брадикардия)")
        else:
            notes.append("Базальная ЧСС в норме")

        last_stv = df["stv_all"].iloc[-1]
        if last_stv < 3:
            notes.append("Низкая STV, возможный риск гипоксии")
        elif last_stv > 6:
            notes.append("Высокая вариабельность")
        else:
            notes.append("STV в пределах нормы")

        acc = df["accelerations_count"].iloc[-1]

        if acc >= 3:
            notes.append(f"Наблюдаются акцелерации ({acc} за день)")
        else:
            notes.append("Акцелерации незначительные")

        X = np.arange(len(df)).reshape(-1, 1)
        y = df["baseline_bpm"].values
        model = LinearRegression().fit(X, y)

        slope = model.coef_[0]
        if slope > 0.6:
            notes.append(f"Тренд на повышение базальной ЧСС (+{slope:.2f} уд/мин в день)")
        elif slope > 0.1:
            notes.append(f"Небольшой тренд на повышение базальной ЧСС (+{slope:.2f} уд/мин в день)")
        elif slope < -0.6:
            notes.append(f"Тренд на снижение базальной ЧСС ({slope:.2f} уд/мин в день)")
        elif slope < -0.1:
            notes.append(f"Небольшой тренд на снижение базальной ЧСС ({slope:.2f} уд/мин в день)")
        else:
            notes.append("Тренд базальной ЧСС стабильный")

        return " | ".join(notes)