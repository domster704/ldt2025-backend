from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.ports.patients import PatientPort


async def get_patient_base_info(patient_id: int, patient_repo: PatientPort):
    patient = await patient_repo.get_by_id(patient_id)
    if not patient:
        raise NotFoundObject
    return patient