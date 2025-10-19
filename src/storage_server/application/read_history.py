from storage_server.domain.ctg_history import CTGHistory
from .dto.ctg_history import CTGHistoryReadOutDTO
from .dto.ctg_result import CTGResultReadOutDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_history_repo import CTGHistoryRepository
from .ports.ctg_result_repo import CTGResultRepository


async def read_ctg_history(
        patient_id: int, ctg_history_repo: CTGHistoryRepository, ctg_result_repo: CTGResultRepository
) -> list[CTGHistoryReadOutDTO]:
    ctg_history_list = []
    try:
        async for ctg_history in ctg_history_repo.read_by_patient_id(patient_id): # type: CTGHistory
            ctg_history_dto = CTGHistoryReadOutDTO.model_validate(ctg_history.to_dict())
            ctg_result = await ctg_result_repo.read_by_ctg_id(ctg_history_dto.id)
            ctg_result_dto = None
            if ctg_result is not None:
                ctg_result_dto = CTGResultReadOutDTO.model_validate(ctg_result.to_dict())
            ctg_history_dto.ctg_result = ctg_result_dto
            ctg_history_list.append(ctg_history_dto)

    except Exception as err:
        raise UnexpectedError from err

    return ctg_history_list