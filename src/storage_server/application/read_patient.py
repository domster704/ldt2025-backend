from .dto.patient import PatientReadOutDTO
from .exceptions.application import UnexpectedError, PatientNotFound
from .ports.patient_repo import PatientRepository

async def read_patient(
        patient_id: int,
        patient_repo: PatientRepository,
) -> PatientReadOutDTO:
    try:
        patient = await patient_repo.read(patient_id)
    except Exception:
        raise UnexpectedError

    if patient is None:
        raise PatientNotFound
    else:
        return PatientReadOutDTO.model_validate(patient.to_dict())
