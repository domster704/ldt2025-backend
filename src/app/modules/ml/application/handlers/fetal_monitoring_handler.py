import pandas as pd

from app.common.ctg import CurrentCtgID
from app.modules.ingest.entities.ctg import CardiotocographyPoint
from app.modules.ml.application.interfaces.fetal_monitoring import IFetalMonitoring
from app.modules.ml.domain.entities.process import Process
from app.modules.ml.infrastucture.services.result_repo import ResultRepository


class FetalMonitoringHandler:
    def __init__(self, fetal_monitoring_service: IFetalMonitoring):
        self.fetal_monitoring_service = fetal_monitoring_service
        self._df = pd.DataFrame()
        self._result_repo = ResultRepository()

    def process_stream(self, points: list[CardiotocographyPoint]) -> Process:
        start_ts = points[0].timestamp
        rows = []
        for p in points:
            # time_sec = p.timestamp - start_ts
            # print(time_sec, p.timestamp, start_ts)
            rows.append({
                "time_sec": p.timestamp,
                "value_bpm": float(p.bpm) if p.bpm is not None else None,
                "value_uterus": float(p.uc) if p.uc is not None else None,
            })
        self._df = pd.DataFrame(rows, columns=["time_sec", "value_bpm", "value_uterus"])

        result: Process = self.fetal_monitoring_service.process_stream(self._df)
        return result

    async def finalize(self) -> None:
        result = self.fetal_monitoring_service.finalize_process()
        await self._result_repo.add_result(CurrentCtgID.get(), result)
