from app.modules.core.usecases.ports.patients import PatientPort


async def get_patient_ctgs(patient_id: int, patient_repo: PatientPort) -> list[int]:
    return await patient_repo.get_ctgs(patient_id)