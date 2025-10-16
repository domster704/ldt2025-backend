from .dto.ctg_result import CTGResultReadOutDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_result_repo import CTGResultRepository


async def read_ctg_result(
        ctg_id: int, ctg_history_repo: CTGResultRepository
) -> list[CTGResultReadOutDTO]:
    ctg_results = []
    try:
        async for ctg_result in ctg_history_repo.read_by_ctg_id(ctg_id):
            ctg_results.append(CTGResultReadOutDTO.model_validate(ctg_result))
    except Exception:
        raise UnexpectedError

    return ctg_results