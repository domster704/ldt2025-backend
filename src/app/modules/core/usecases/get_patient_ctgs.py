from collections.abc import Iterable

from sqlalchemy.util import await_only

from app.modules.core.domain.ctg import CTGHistory
from app.modules.core.usecases.ports.ctg_repository import CTGRepository
from app.modules.core.usecases.ports.patient_repository import PatientRepository


async def get_patient_ctgs(
        patient_id: int, patient_repo: PatientRepository, ctg_repo: CTGRepository
) -> Iterable[CTGHistory]:
    ctgs_ids = list(await patient_repo.get_ctgs(patient_id))

    ctg_dict = {ctg.id: ctg for ctg in await ctg_repo.list_ctg(ctgs_ids)}
    for result in await ctg_repo.list_results(ctgs_ids):
        if result.ctg_id in ctg_dict.keys():
            ctg_dict[result.ctg_id].result = result

    return ctg_dict.values()
