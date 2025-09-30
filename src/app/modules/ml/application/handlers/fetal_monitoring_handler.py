import pandas as pd

from app.modules.ingest.entities.ctg import CardiotocographyPoint
from app.modules.ml.application.interfaces.fetal_monitoring import IFetalMonitoring
from app.modules.ml.domain.entities.process import Process


class FetalMonitoringHandler:
    def __init__(self, fetal_monitoring_service: IFetalMonitoring):
        self.fetal_monitoring_service = fetal_monitoring_service

    def process_stream(self, points: list[CardiotocographyPoint]) -> Process:
        df = pd.DataFrame()

        start_ts = points[0].timestamp
        rows = []
        for p in points:
            time_sec = p.timestamp - start_ts
            rows.append({
                "time_sec": time_sec,
                "value_bpm": float(p.bpm) if p.bpm is not None else None,
                "value_uterus": float(p.uc) if p.uc is not None else None,
            })
        df = pd.DataFrame(rows, columns=["time_sec", "value_bpm", "value_uterus"])

        result: Process = self.fetal_monitoring_service.process_stream(df)
        return result
