import httpx
from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, UploadFile, HTTPException, File
from starlette import status

from app.common.settings import AppSettings

router = APIRouter()

@router.post(
    '/extract-signals',
    description="Запуск эмулятора"
)
async def extract_bpm_uc_signals(
        app_settings: FromDishka[AppSettings],
        archive: UploadFile = File(...),
):
    try:
        content = await archive.read()

        async with httpx.AsyncClient(base_url=app_settings.emulator_uri) as client:
            resp = await client.post(
                '/start',
                files={"file": (archive.filename, content, archive.content_type)}
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Не удалось запустить эмулятор'
                )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при передаче архива: {e}"
        )
