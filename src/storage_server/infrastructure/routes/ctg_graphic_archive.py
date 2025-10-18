from datetime import datetime

from dishka.integrations.fastapi import inject, FromDishka
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse

from storage_server.settings import AppSettings
from storage_server.application.add_ctg_graphic_file import add_ctg_graphic_file
from storage_server.application.dto.ctg_graphic_file import CTGGraphicFileAddInDTO
from storage_server.application.exceptions.application import UnexpectedError
from storage_server.application.get_ctg_graphic_archive import get_ctg_graphic_archive_path
from storage_server.application.ports.ctg_history_repo import CTGHistoryRepository

router = APIRouter()


@router.get("")
@inject
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

    return FileResponse(archive_path)

@router.put("")
@inject
async def add_ctg_graphic(
        patient_id: int,
        ctg_datetime: str,
        ctg_history_repo: FromDishka[CTGHistoryRepository],
        app_settings: FromDishka[AppSettings],
        upload_file: UploadFile = File(...),
) -> None:
    try:
        datetime_real = datetime.strptime(ctg_datetime, "%Y%m%d%H%M%S")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid datetime')
    try:
        file = await upload_file.read()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid file')
    dto = CTGGraphicFileAddInDTO(
        patient_id=patient_id,
        ctg_datetime=datetime_real,
        file=file,
    )
    try:
        await add_ctg_graphic_file(dto, ctg_history_repo, app_settings.archive_base_dir)
    except UnexpectedError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Unexpected error')
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)