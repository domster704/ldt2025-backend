from dishka import FromDishka
from fastapi import APIRouter, HTTPException, status

from ...application.exceptions.application import PatientNotFound, UnexpectedError
from ...application.exceptions.patient_repository import PatientExists
from ...application.ports.patient_repo import PatientRepository
from ...application.read_patient import read_patient
from ...domain.patient import Patient

router = APIRouter()


@router.get("/{patient_id}")
async def get_patient(patient_id: int, patient_repo: FromDishka[PatientRepository]) -> Patient:
    try:
        return await read_patient(patient_id, patient_repo)
    except PatientNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_INTERNAL_SERVER_ERROR)

@router.put("", status_code=status.HTTP_201_CREATED)
async def create_patient(patient: Patient, patient_repo: FromDishka[PatientRepository]) -> None:
    try:
        await create_patient(patient, patient_repo)
    except PatientExists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient already exists")
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_INTERNAL_SERVER_ERROR)

@router.patch("")
async def update_patient(patient: Patient, patient_repo: FromDishka[PatientRepository]) -> None:
    try:
        await update_patient(patient, patient_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_INTERNAL_SERVER_ERROR)