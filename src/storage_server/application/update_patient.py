from .dto.patient import PatientUpdateInDTO
from .exceptions.application import UnexpectedError
from .ports.patient_repo import PatientRepository
from ..domain.patient import Patient

async def update_patient(patient_dto: PatientUpdateInDTO, patient_repo: PatientRepository) -> None:
    patient = Patient.from_dto(patient_dto)
    try:
        await patient_repo.save(patient)
    except Exception as err:
        raise UnexpectedError from err