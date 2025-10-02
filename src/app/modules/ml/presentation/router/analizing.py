import pandas as pd
from dishka.integrations.fastapi import inject, FromDishka
from fastapi import APIRouter, Depends, HTTPException

from app.modules.core.usecases.ports.ctg import CTGPort
from app.modules.core.usecases.ports.patients import PatientPort
from app.modules.ml.application.handlers.fetal_monitoring_handler import FetalMonitoringHandler
from app.modules.ml.infrastucture.di import get_fetal_monitoring_handler

router = APIRouter()

@router.get("/analizing/{patient_id}")
@inject
async def analyze(
        patient_id: int,
        patient_repo: FromDishka[PatientPort],
        ctg_repo: FromDishka[CTGPort],
        fetal_monitoring_handler: FetalMonitoringHandler = Depends(get_fetal_monitoring_handler)
):
    df = pd.DataFrame(columns=["day", "baseline_bpm", "stv_all", "accelerations_count"])
    ctgs = await patient_repo.get_ctgs(patient_id)

    ctg_ids = [ctg.id for ctg in await ctg_repo.list_ctg(ctgs)]
    result_list = [
        {
            "day": result.timestamp,
            "baseline_bpm": result.bpm,
            "stv_all": result.stv or 100,
            "accelerations_count": result.accelerations
        }
        for result in await ctg_repo.list_results(ctg_ids)
    ]
    df = pd.DataFrame(result_list).sort_values(by="day")
    print(df.head())
    try:
        return {
            "analysis": fetal_monitoring_handler.fetal_monitoring_service.analyze_patient_dynamics(df)
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Could not analyze patient")