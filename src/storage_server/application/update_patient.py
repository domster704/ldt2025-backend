from .exceptions.application import UnexpectedError
from .ports.patient_repo import PatientRepository
from ..domain.patient import Patient

async def create_patient(patient: Patient, patient_repo: PatientRepository) -> None:
    try:
        await patient_repo.save(patient)
    except Exception:
        raise UnexpectedError