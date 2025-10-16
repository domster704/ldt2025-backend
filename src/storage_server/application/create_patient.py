from .exceptions.application import UnexpectedError
from .exceptions.patient_repository import PatientExists
from .ports.patient_repo import PatientRepository
from ..domain.patient import Patient


async def create_patient(patient: Patient, patient_repo: PatientRepository) -> None:
    try:
        patient_exists = await patient_repo.is_exists(patient.id)
    except Exception:
        raise UnexpectedError

    if patient_exists:
        raise PatientExists
    try:
        await patient_repo.save(patient)
    except Exception:
        raise UnexpectedError