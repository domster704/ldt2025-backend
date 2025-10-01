from app.modules.core.domain.patient import Patient
from app.modules.core.usecases.ports.patients import PatientPort


async def get_patients_list(patient_ids: list[int] | None, patient_repo: PatientPort) -> list[Patient]:
    return await patient_repo.list(patient_ids)