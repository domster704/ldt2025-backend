from collections.abc import Iterable

from app.modules.core.domain.ctg import CTGHistory
from app.modules.core.usecases.ports.ctg import CTGPort
from app.modules.core.usecases.ports.patients import PatientPort


async def get_patient_ctgs(
        patient_id: int, patient_repo: PatientPort, ctg_repo: CTGPort
) -> Iterable[CTGHistory]:
    ctgs_ids = await patient_repo.get_ctgs(patient_id)

    ctg_dict = {ctg.id: ctg for ctg in await ctg_repo.list_ctg(ctgs_ids)}
    for result in await ctg_repo.list_results(ctgs_ids):
        if result.ctg_id in ctg_dict:
            ctg_dict[result.ctg_id].result = result

    return ctg_dict.values()
