from dishka.integrations.fastapi import inject, FromDishka
from fastapi import APIRouter, HTTPException
from starlette import status

from storage_server.application.dto.ctg_result import CTGResultReadOutDTO, CTGResultAddInDTO
from storage_server.application.exceptions.application import UnexpectedError
from storage_server.application.ports.ctg_result_repo import CTGResultRepository
from storage_server.application.read_ctg_result import read_ctg_result
from storage_server.application.save_ctg_result import save_ctg_result

router = APIRouter()


@router.post("")
@inject
async def get_ctg_result(
        ctg_id: int, ctg_result_repo: FromDishka[CTGResultRepository]
) -> list[CTGResultReadOutDTO]:
    try:
        return await read_ctg_result(ctg_id, ctg_result_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.put("")
@inject
async def create_ctg_result(
        body: CTGResultAddInDTO, ctg_result_repo: FromDishka[CTGResultRepository]
) -> None:
    try:
        await save_ctg_result(body, ctg_result_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
