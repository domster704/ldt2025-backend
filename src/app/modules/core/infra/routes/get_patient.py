from collections.abc import Sequence
from typing import Annotated

from dishka import FromComponent
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException
from starlette import status

from app.common.patient import CurrentPatientID
from app.modules.core.domain.patient import Patient
from app.modules.core.infra.message_builder import AnamnesisMessageBuilder
from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.get_patient import get_patient, get_all_patients
from app.modules.core.usecases.load_all_patient_info import load_all_patient_info
from app.modules.core.usecases.ports.ctg_repository import CTGRepository
from app.modules.core.usecases.ports.llm_gateway import LLMGateway
from app.modules.core.usecases.ports.patient_gateway import PatientGateway
from app.modules.core.usecases.ports.patient_repository import PatientRepository

router = APIRouter()

@router.get('/patients/{patient_id}')
@inject
async def get_patient_info(
        patient_id: int,
        patient_gtw: Annotated[PatientGateway, FromComponent("external_server")],
        patient_repo: FromDishka[PatientRepository],
        llm_gateway: Annotated[LLMGateway, FromComponent("llm")],
        ctg_repo: FromDishka[CTGRepository],
) -> Patient:
    CurrentPatientID.set(patient_id)

    try:
        await load_all_patient_info(
            patient_id, patient_gtw, patient_repo, llm_gateway, AnamnesisMessageBuilder(), ctg_repo
        )
    except Exception as e:
        pass
    try:
        patient = await get_patient(patient_id, patient_repo)
    except NotFoundObject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id={patient_id} not found"
        )
    return patient

@router.get('/patients')
@inject
async def get_all_patients_endpoint(patient_repo: FromDishka[PatientRepository]) -> Sequence[Patient]:
    try:
        patients = await get_all_patients(patient_repo)
    except NotFoundObject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patients cannot be retrieved"
        )
    return patients
