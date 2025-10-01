from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.domain.patient import PatientAdditionalInfo
from app.modules.core.usecases.ports.patients import PatientPort


async def get_patient_additional_info(patient_id: int, patient_repo: PatientPort) -> PatientAdditionalInfo:
    add_info = await patient_repo.get_additional_info(patient_id)
    if not add_info:
        raise NotFoundObject
    return add_info