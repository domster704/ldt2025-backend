from dishka import FromDishka
from fastapi import APIRouter, HTTPException
from starlette import status

from storage_server.application.dto.ctg_history import CTGHistoryAddInDTO, CTGHistoryReadOutDTO
from storage_server.application.exceptions.application import UnexpectedError
from storage_server.application.ports.ctg_history_repo import CTGHistoryRepository
from storage_server.application.read_history import read_ctg_history
from storage_server.application.save_ctg_history import save_ctg_history

router = APIRouter()


@router.post("")
async def get_ctg_history(
        patient_id: int, ctg_history_repo: FromDishka[CTGHistoryRepository]
) -> list[CTGHistoryReadOutDTO]:
    try:
        return await read_ctg_history(patient_id, ctg_history_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.put("")
async def create_ctg_history(
        body: CTGHistoryAddInDTO, ctg_history_repo: FromDishka[CTGHistoryRepository]
) -> None:
    try:
        await save_ctg_history(body, ctg_history_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)