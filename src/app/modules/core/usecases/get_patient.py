from app.modules.core.domain.patient import Patient
from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.ports.patients import PatientPort


async def get_patient(patient_id: int, patient_repo: PatientPort) -> Patient:
    patient = await patient_repo.get_by_id(patient_id)
    if not patient:
        raise NotFoundObject
    patient.additional_info = await patient_repo.get_additional_info(patient_id)

    return patient
