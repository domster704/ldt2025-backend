from dishka import FromDishka
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ...settings import AppSettings
from ...application.add_ctg_graphic_file import add_ctg_graphic_file
from ...application.dto.ctg_graphic_file import CTGGraphicFileAddInDTO
from ...application.exceptions.application import UnexpectedError
from ...application.get_ctg_graphic_archive import get_ctg_graphic_archive_path
from ...application.ports.ctg_history_repo import CTGHistoryRepository

router = APIRouter()


@router.get("/get_archive")
async def get_ctg_graphic_archive(
        patient_id: int,
        ctg_history_repo: FromDishka[CTGHistoryRepository]
) -> FileResponse:
    try:
        archive_path = await get_ctg_graphic_archive_path(patient_id, ctg_history_repo)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ...

@router.put("/add_graphic")
async def add_ctg_graphic(
        body: CTGGraphicFileAddInDTO,
        ctg_history_repo: FromDishka[CTGHistoryRepository],
        app_settings: FromDishka[AppSettings]
) -> None:
    try:
        await add_ctg_graphic_file(body, ctg_history_repo, app_settings.archive_base_dir)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)