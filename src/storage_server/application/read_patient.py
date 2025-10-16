from .exceptions.application import UnexpectedError, PatientNotFound
from .ports.patient_repo import PatientRepository
from ..domain.patient import Patient


async def read_patient(
        patient_id: int,
        patient_repo: PatientRepository,
) -> Patient:
    try:
        patient = await patient_repo.read(patient_id)
    except Exception:
        raise UnexpectedError

    if patient is None:
        raise PatientNotFound
    else:
        return patient
