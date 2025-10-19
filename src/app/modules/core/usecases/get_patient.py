from typing import Sequence

from app.modules.core.domain.patient import Patient
from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.ports.patient_repository import PatientRepository


async def get_patient(patient_id: int, patient_repo: PatientRepository) -> Patient:
    patient = await patient_repo.get_by_id(patient_id)
    if not patient:
        raise NotFoundObject
    patient.additional_info = await patient_repo.get_additional_info(patient_id)

    return patient


async def get_all_patients(patient_repo: PatientRepository) -> Sequence[Patient]:
    return await patient_repo.get_all()
