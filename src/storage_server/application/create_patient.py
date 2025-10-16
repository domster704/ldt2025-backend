from .dto.patient import PatientAddInDTO
from .exceptions.application import UnexpectedError
from .exceptions.patient_repository import PatientExists
from .ports.patient_repo import PatientRepository
from ..domain.patient import Patient


async def create_patient(patient_dto: PatientAddInDTO, patient_repo: PatientRepository) -> None:
    try:
        patient_exists = await patient_repo.is_exists(patient_dto.id)
    except Exception:
        raise UnexpectedError
    if patient_exists:
        raise PatientExists

    patient = Patient.from_dto(patient_dto)
    try:
        await patient_repo.save(patient)
    except Exception:
        raise UnexpectedError