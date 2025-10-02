from typing import Protocol

import pandas as pd

from app.modules.ml.domain.entities.process import Process, ProcessResults


class IFetalMonitoring(Protocol):
    def process_stream(self, df: pd.DataFrame) -> Process:
        """
        Вызывается раз в секунду. Обновляет внутреннее состояние и отдаёт last_notification.
        """
        ...

    def finalize_process(self) -> ProcessResults:
        """
        Итоговые метрики по накопленным данным.
        Возвращает dict:
          - last_figo
          - baseline_bpm (10 мин медиана на конце)
          - stv_all (по всей записи)
          - stv_10min_mean (среднее по всем 10-мин окнам)
          - accelerations_count
          - decelerations_count
          - uterus_mean
        """
        ...

    @staticmethod
    def analyze_patient_dynamics(df: pd.DataFrame) -> str:
        """
        Пример использования:

        df = pd.DataFrame({
            "day": days,
            "baseline_bpm": ...,
            "stv_all": ...,
            "accelerations_count": ...,
        })

        0,2025-09-20,142.6,2.87,5
        1,2025-09-21,139.3,4.94,4
        """
        ...
