from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException
from starlette import status

from app.modules.core.domain.patient import Patient
from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.get_patient import get_patient
from app.modules.core.usecases.ports.patients import PatientPort

router = APIRouter()

@router.get('/patients/{patient_id}')
@inject
async def get_patient_info(patient_id: int, patient_repo: FromDishka[PatientPort]) -> Patient:
    try:
        patient = await get_patient(patient_id, patient_repo)
    except NotFoundObject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id={patient_id} not found"
        )
    return patient
