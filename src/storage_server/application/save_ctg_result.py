from ..domain.ctg_result import CTGResult
from .dto.ctg_result import CTGResultAddInDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_result_repo import CTGResultRepository


async def save_ctg_result(ctg_result_dto: CTGResultAddInDTO, ctg_result_repo: CTGResultRepository) -> None:
    ctg_result = CTGResult.from_dto(ctg_result_dto)
    try:
        await ctg_result_repo.save(ctg_result_dto.ctg_id, ctg_result)
    except Exception as err:
        raise UnexpectedError from err