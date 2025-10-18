from dishka.integrations.fastapi import inject, FromDishka
from fastapi import APIRouter, HTTPException, status

from storage_server.application.create_patient import create_patient
from storage_server.application.update_patient import update_patient
from storage_server.application.dto.patient import PatientReadOutDTO, PatientAddInDTO, PatientUpdateInDTO
from storage_server.application.exceptions.application import PatientNotFound, UnexpectedError
from storage_server.application.exceptions.patient_repository import PatientExists
from storage_server.application.ports.patient_repo import PatientRepository
from storage_server.application.read_patient import read_patient

router = APIRouter()


@router.get("/{patient_id}")
@inject
async def get_patient(patient_id: int, patient_repo: FromDishka[PatientRepository]) -> PatientReadOutDTO:
    try:
        return await read_patient(patient_id, patient_repo)
    except PatientNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.put("", status_code=status.HTTP_201_CREATED)
@inject
async def add_patient(patient: PatientAddInDTO, patient_repo: FromDishka[PatientRepository]) -> None:
    try:
        await create_patient(patient, patient_repo)
    except PatientExists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient already exists")
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.patch("")
@inject
async def update_patient_info(patient: PatientUpdateInDTO, patient_repo: FromDishka[PatientRepository]) -> None:
    try:
        await update_patient(patient, patient_repo)
    except UnexpectedError as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)