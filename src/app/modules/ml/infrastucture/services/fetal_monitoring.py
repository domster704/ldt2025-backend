from collections import deque

import numpy as np
import pandas as pd

from app.modules.ml.application.interfaces.fetal_monitoring import IFetalMonitoring
from app.modules.ml.domain.entities.process import Process, TimeRange


class FetalMonitoringService(IFetalMonitoring):
    """
    Реал-тайм сервис для анализа FHR (value_bpm) и UC (value_uterus) со стримового ввода.
    Предполагается, что process_stream вызывается раз в секунду и ему передают df
    с новыми строками (или всем df — он сам отфильтрует до текущей секунды).
    """

    def __init__(self, model_config):
        self.model_config = model_config
        self.model = model_config['model']
        self.features = model_config['features']
        self.target = model_config['target']
        self.window_size = model_config['window_size']
        self.step_size = model_config['step_size']
        self.fs = model_config['fs']  # частота исходного сигнала, если нужна

        self.window_last_second = 0
        self.current_df = None

        # Пороговая логика
        self.tachycardia_seconds_threshold = 10  # как часто обновлять уведомление
        self.tachycardia_bpm_threshold = 160

        # Настройки событий акцелераций/децелераций
        self.accel_delta_bpm = 15
        self.decel_delta_bpm = -15
        self.min_event_duration_sec = 15
        self.local_baseline_window_sec = 60  # для локального базиса

        # Истории посекундных средних для онлайна
        # Храним (t, value); maxlen ~ 30 мин, чтобы хватало для 10-мин и 5-мин окон
        self.sec_fhr = deque(maxlen=1800)
        self.sec_uc = deque(maxlen=1800)

        # Состояния текущих (активных) эпизодов
        self.active_accel = None  # dict: {'start': t0, 'count': k, 'announced': False, 'list_idx': int}
        self.active_decel = None

        self.last_notification = {
            'tachycardia': "Недостаточно данных",
            'hypoxia_proba': None,

            # 1) Акцелерации/децелерации — список словарей {'start': t0, 'end': t1 или None}
            'accelerations': [],
            'decelerations': [],

            # 2) Медианный ЧСС за 10 минут
            'median_fhr_10min': None,

            # 3) Текущий ЧСС и 4) текущий uterus (посекундные средние)
            'current_fhr': None,
            'current_uterus': None,

            # 5) STV за 5 минут (аппроксимация по посекундным средним)
            'stv_5min': None,

            # вспомогательное
            'time_sec': 0,
        }

    # ====== Внутренние утилиты ======

    def _slice_last_seconds(self, deq, now_t, seconds):
        """Вернуть список значений из deque за последние 'seconds' секунд (включая now_t)."""
        lo = now_t - seconds + 1
        vals = [v for (t, v) in deq if t >= lo and t <= now_t and pd.notna(v)]
        return vals

    def _median_last_seconds(self, deq, now_t, seconds):
        vals = self._slice_last_seconds(deq, now_t, seconds)
        return float(np.median(vals)) if len(vals) > 0 else None

    def _mean_abs_diff_last_seconds(self, deq, now_t, seconds):
        """Среднее |Δ| по посекундным средним за окно seconds (STV-аппроксимация)."""
        series = [(t, v) for (t, v) in deq if t > now_t - seconds and t <= now_t and pd.notna(v)]
        if len(series) < 2:
            return None
        # series уже по возрастанию t; считаем |Δ|
        diffs = []
        prev = series[0][1]
        for _, v in series[1:]:
            if pd.notna(prev) and pd.notna(v):
                diffs.append(abs(v - prev))
            prev = v
        return float(np.mean(diffs)) if len(diffs) else None

    def _second_mean(self, df, end_second):
        """Среднее значение в (end_second-1, end_second] по колонке; если нет данных — np.nan."""
        start = end_second - 1
        sl = df[(df['time_sec'] > start) & (df['time_sec'] <= end_second)]
        return sl['value_bpm'].mean(), sl['value_uterus'].mean()

    # ====== Фичи и модель ======

    def create_window(self, df):
        df_temp = df[df['time_sec'] <= self.window_last_second].copy()
        df_temp['window_time_max'] = self.window_last_second
        return df_temp

    def extract_features(self, window_df):
        if window_df.empty:
            return {**{f: np.nan for f in self.features}}

        fhr = window_df["value_bpm"].astype(float).values
        uc = window_df["value_uterus"].astype(float).values
        window_time = window_df["window_time_max"].values[0]

        rr_diff = np.diff(fhr)
        sdnn = np.std(fhr) if len(fhr) else np.nan
        rmssd = np.sqrt(np.mean(rr_diff ** 2)) if len(rr_diff) > 0 else np.nan
        pnn50 = np.mean(np.abs(rr_diff) > 50) if len(rr_diff) > 0 else np.nan  # упрощенно

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

        # Корреляция FHR-UC
        corr = np.corrcoef(fhr, uc)[0, 1] if (len(fhr) > 1 and np.std(uc) > 0 and np.std(fhr) > 0) else np.nan

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

    def _update_tachycardia(self, now_t):
        """
        Оцениваем базальную ЧСС по 10-мин окну по посекундным средним (аппроксимация),
        обновляем каждые self.tachycardia_seconds_threshold секунд.
        """
        if now_t % self.tachycardia_seconds_threshold != 0:
            return

        # Базис/базальная ЧСС: медиана за 10 минут
        median_10 = self._median_last_seconds(self.sec_fhr, now_t, 600)
        self.last_notification['median_fhr_10min'] = median_10

        if median_10 is None:
            self.last_notification['tachycardia'] = "Недостаточно данных"
            return

        if median_10 > self.tachycardia_bpm_threshold:
            deviation = round(median_10 - self.tachycardia_bpm_threshold, 1)
            self.last_notification[
                'tachycardia'] = f"Подозрение на тахикардию (базальная ≈ {median_10:.1f} bpm, +{deviation} bpm)."
        else:
            self.last_notification['tachycardia'] = f"Нет признаков тахикардии (базальная ≈ {median_10:.1f} bpm)."

    def _update_stv(self, now_t):
        """STV за последние 5 минут (300 с), обновляем каждые 10 с."""
        if now_t % 10 != 0:
            return
        stv = self._mean_abs_diff_last_seconds(self.sec_fhr, now_t, 300)
        self.last_notification['stv_5min'] = None if stv is None else float(round(stv, 2))

    def _update_accel_decel(self, now_t):
        """
        Детекция акцелераций/децелераций относительно локального базиса (медиана 60 с).
        Логика:
          - если |Δ| пересек порог и держится ≥15 с — формируем событие с end=None;
          - когда вернулись к базису — закрываем событие (проставляем end).
        """
        # Текущая посекундная FHR
        if not self.sec_fhr or self.sec_fhr[-1][0] != now_t:
            return  # нет свежего значения

        curr_fhr = self.sec_fhr[-1][1]
        if pd.isna(curr_fhr):
            return

        baseline = self._median_last_seconds(self.sec_fhr, now_t, self.local_baseline_window_sec)
        if baseline is None:
            return

        delta = curr_fhr - baseline

        # --- Акцелерации ---
        if delta >= self.accel_delta_bpm and self.active_decel is None:
            if self.active_accel is None:
                self.active_accel = {'start': now_t, 'count': 1, 'announced': False, 'list_idx': None}
            else:
                self.active_accel['count'] += 1

            # как только дотянули до min_event_duration_sec — объявляем (append с end=None)
            if (not self.active_accel['announced']) and self.active_accel['count'] >= self.min_event_duration_sec:
                self.last_notification['accelerations'].append({'start': self.active_accel['start'], 'end': None})
                self.active_accel['list_idx'] = len(self.last_notification['accelerations']) - 1
                self.active_accel['announced'] = True

        else:
            # выходим из зоны акцелерации
            if self.active_accel is not None:
                if self.active_accel['announced'] and self.active_accel['list_idx'] is not None:
                    # закрываем событие концом на предыдущей секунде (now_t - 1)
                    idx = self.active_accel['list_idx']
                    if self.last_notification['accelerations'][idx]['end'] is None:
                        self.last_notification['accelerations'][idx]['end'] = now_t - 1
                # сброс состояния
                self.active_accel = None

        # --- Децелерации ---
        if delta <= self.decel_delta_bpm and self.active_accel is None:
            if self.active_decel is None:
                self.active_decel = {'start': now_t, 'count': 1, 'announced': False, 'list_idx': None}
            else:
                self.active_decel['count'] += 1

            if (not self.active_decel['announced']) and self.active_decel['count'] >= self.min_event_duration_sec:
                self.last_notification['decelerations'].append({'start': self.active_decel['start'], 'end': None})
                self.active_decel['list_idx'] = len(self.last_notification['decelerations']) - 1
                self.active_decel['announced'] = True

        else:
            if self.active_decel is not None:
                if self.active_decel['announced'] and self.active_decel['list_idx'] is not None:
                    idx = self.active_decel['list_idx']
                    if self.last_notification['decelerations'][idx]['end'] is None:
                        self.last_notification['decelerations'][idx]['end'] = now_t - 1
                self.active_decel = None

    def tachycardia_notification(self, df):
        """
        Оставил для совместимости, но используем 10-мин медиану из self.sec_fhr.
        Если её нет, fallback на mean по текущему df.
        """
        median_10 = self.last_notification.get('median_fhr_10min')
        if median_10 is not None:
            if median_10 > self.tachycardia_bpm_threshold:
                deviation = round(median_10 - self.tachycardia_bpm_threshold, 1)
                return f"Подозрение на тахикардию (базальная ≈ {median_10:.1f} bpm, +{deviation} bpm)."
            return f"Нет признаков тахикардии (базальная ≈ {median_10:.1f} bpm)."

        # Fallback — не идеален, но лучше, чем ничего
        if df.empty or 'value_bpm' not in df.columns:
            return "Недостаточно данных"
        mean_bpm = df['value_bpm'].mean()
        if pd.isna(mean_bpm):
            return "Недостаточно данных"
        if mean_bpm > self.tachycardia_bpm_threshold:
            deviation = round(mean_bpm - self.tachycardia_bpm_threshold, 1)
            return f"Подозрение на тахикардию. Отклонение от нормы на {deviation} bpm"
        return "Нет признаков тахикардии"

    # ====== Главный метод стриминга ======

    def process_stream(self, df: pd.DataFrame) -> Process | None:
        """
        Вызывается раз в секунду. Обновляет внутреннее состояние и отдаёт last_notification.
        """
        self.window_last_second += 1

        # Обновляем накопленный df до текущей секунды
        if self.current_df is None:
            self.current_df = df[df['time_sec'] <= self.window_last_second].copy()
        else:
            new_part = df[(df['time_sec'] > self.current_df['time_sec'].max()) &
                          (df['time_sec'] <= self.window_last_second)].copy()
            # На случай, если подаёшь весь df каждый раз:
            if new_part.empty:
                new_part = df[(df['time_sec'] <= self.window_last_second) &
                              (df['time_sec'] > self.current_df['time_sec'].max())].copy()
            if not new_part.empty:
                self.current_df = pd.concat([self.current_df, new_part], ignore_index=True)

        # Посекундные средние (текущие значения за последнюю секунду)
        curr_fhr, curr_uc = (np.nan, np.nan)
        if self.current_df is not None and not self.current_df.empty:
            curr_fhr, curr_uc = self._second_mean(self.current_df, self.window_last_second)

        # Обновляем истории
        self.sec_fhr.append((self.window_last_second, float(curr_fhr) if pd.notna(curr_fhr) else np.nan))
        self.sec_uc.append((self.window_last_second, float(curr_uc) if pd.notna(curr_uc) else np.nan))

        # 3) текущий FHR & 4) текущий UC (посекундные средние)
        self.last_notification['current_fhr'] = None if pd.isna(curr_fhr) else float(round(curr_fhr, 2))
        self.last_notification['current_uterus'] = None if pd.isna(curr_uc) else float(round(curr_uc, 2))

        # Модель: раз в window_size сек
        model_output_proba = None
        if self.window_last_second % self.window_size == 0:
            window_df = self.create_window(self.current_df)
            features = self.extract_features(window_df)
            model_input = pd.DataFrame([features])
            try:
                model_output_proba = self.model.predict_proba(model_input)[:, 1].item()
            except Exception:
                model_output_proba = None
            self.last_notification['hypoxia_proba'] = model_output_proba

        # 2) Медиана ЧСС 10 мин + уведомление о тахикардии (каждые X сек)
        self._update_tachycardia(self.window_last_second)

        # 5) STV 5 мин (каждые 10 сек)
        self._update_stv(self.window_last_second)

        # 1) Акцелерации/децелерации по локальному базису
        self._update_accel_decel(self.window_last_second)

        self.last_notification['time_sec'] = self.window_last_second

        accelerations = [
            TimeRange(start=a['start'], end=a['end'] if a['end'] is not None else self.window_last_second)
            for a in self.last_notification['accelerations']
        ]
        decelerations = [
            TimeRange(start=d['start'], end=d['end'] if d['end'] is not None else self.window_last_second)
            for d in self.last_notification['decelerations']
        ]

        return Process(
            tachycardia=self.last_notification['tachycardia'],
            hypoxia_proba=self.last_notification['hypoxia_proba'],
            accelerations=accelerations,
            decelerations=decelerations,
            median_fhr_10min=self.last_notification['median_fhr_10min'],
            current_fhr=self.last_notification['current_fhr'],
            current_uterus=self.last_notification['current_uterus'],
            stv_5min=self.last_notification['stv_5min'],
            time_sec=self.last_notification['time_sec'],
        )
