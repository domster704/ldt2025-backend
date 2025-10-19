from collections.abc import Iterable

from fastapi import APIRouter
from dishka.integrations.fastapi import FromDishka, inject

from app.modules.core.domain.ctg import CTGHistory
from app.modules.core.usecases.get_patient_ctgs import get_patient_ctgs
from app.modules.core.usecases.ports.ctg_repository import CTGRepository
from app.modules.core.usecases.ports.patient_repository import PatientRepository

router = APIRouter()

@router.get("/ctg_histories")
@inject
async def patient_ctgs(
        patient: int, patient_repo: FromDishka[PatientRepository], ctg_repo: FromDishka[CTGRepository]
) -> Iterable[CTGHistory]:
    return await get_patient_ctgs(patient, patient_repo, ctg_repo)
