from .dto.ctg_history import CTGHistoryAddInDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_history_repo import CTGHistoryRepository
from ..domain.ctg_history import CTGHistory


async def save_ctg_history(ctg_history_dto: CTGHistoryAddInDTO, ctg_history_repo: CTGHistoryRepository) -> None:
    ctg_history = CTGHistory.from_dto(ctg_history_dto)
    try:
        await ctg_history_repo.save(ctg_history_dto.patient_id, ctg_history)
    except Exception:
        raise UnexpectedError