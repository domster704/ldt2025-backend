import pandas as pd
from dishka import FromDishka
from fastapi import APIRouter, Depends

from app.modules.core.usecases.ports.ctg import CTGPort
from app.modules.core.usecases.ports.patients import PatientPort
from app.modules.ml.application.handlers.fetal_monitoring_handler import FetalMonitoringHandler
from app.modules.ml.infrastucture.di import get_fetal_monitoring_handler

router = APIRouter()

@router.get("/analizing/{patient_id}")
async def analyze(
        patient_id: int,
        patient_repo: FromDishka[PatientPort],
        ctg_repo: FromDishka[CTGPort],
        fetal_monitoring_handler: FetalMonitoringHandler = Depends(get_fetal_monitoring_handler)
):
    df = pd.DataFrame()
    ctgs = await patient_repo.get_ctgs(patient_id)

    ctg_ids = [ctg.id for ctg in await ctg_repo.list_ctg(ctgs)]
    result_list = await ctg_repo.list_results(ctg_ids)
    for result in sorted(result_list, key=lambda x: x.timestamp):
        df.add({
            "day": result.timestamp,
            "baseline_bpm": result.bpm,
            "stv_all": result.stv,
            "accelerations_count": result.accellations
        })

    return fetal_monitoring_handler.fetal_monitoring_service.analyze_patient_dynamics(df)