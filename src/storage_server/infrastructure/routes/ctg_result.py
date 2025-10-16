from dishka import FromDishka
from fastapi import APIRouter, HTTPException
from starlette import status

from ...application.dto.ctg_result import CTGResultReadOutDTO, CTGResultAddInDTO
from ...application.exceptions.application import UnexpectedError
from ...application.ports.ctg_result_repo import CTGResultRepository
from ...application.read_ctg_result import read_ctg_result
from ...application.save_ctg_result import save_ctg_result

router = APIRouter()


@router.post("")
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
async def create_ctg_result(
        body: CTGResultAddInDTO, ctg_result_repo: FromDishka[CTGResultRepository]
) -> None:
    try:
        await save_ctg_result(body, ctg_result_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
