from .dto.ctg_history import CTGHistoryReadOutDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_history_repo import CTGHistoryRepository

async def read_ctg_history(
        patient_id: int, ctg_history_repo: CTGHistoryRepository
) -> list[CTGHistoryReadOutDTO]:
    cth_history = []
    try:
        async for ctg_history in ctg_history_repo.read_by_patient_id(patient_id):
            cth_history.append(CTGHistoryReadOutDTO.model_validate(ctg_history.to_dict()))
    except Exception as err:
        raise UnexpectedError from err

    return cth_history