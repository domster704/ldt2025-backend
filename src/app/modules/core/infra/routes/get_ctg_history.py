from collections.abc import Iterable

from fastapi import APIRouter
from dishka.integrations.fastapi import FromDishka, inject

from app.modules.core.domain.ctg import CTGHistory
from app.modules.core.usecases.get_patient_ctgs import get_patient_ctgs
from app.modules.core.usecases.ports.ctg import CTGPort
from app.modules.core.usecases.ports.patients import PatientPort

router = APIRouter()

@router.get("/ctg_histories")
@inject
async def patient_ctgs(
        patient: int, patient_repo: FromDishka[PatientPort], ctg_repo: FromDishka[CTGPort]
) -> Iterable[CTGHistory]:
    return await get_patient_ctgs(patient, patient_repo, ctg_repo)
