import tempfile
import zipfile
import os
from typing import Any

from fastapi import APIRouter, UploadFile, HTTPException, File
from starlette import status
from starlette.responses import StreamingResponse

from app.modules.core.usecases.extract_material_sginals import extract_material_signals

router = APIRouter()

@router.post(
    '/extract-bpm-uc-signals',
    description="Обработка архива с записями о ЧСС и МС"
)
async def extract_bpm_uc_signals(archive: UploadFile = File(...)):
    if not archive.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be zip archive"
        )

    chunk_size = 1024 * 1024
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = tmp.name
    while True:
        chunk = await archive.read(1024 * 1024)
        if not chunk:
            break
        tmp.write(chunk)
    tmp.flush()
    tmp.seek(0)


    def json_iter() -> Any:
        try:
            tmp.seek(0)
            with zipfile.ZipFile(tmp) as zf:
                yield from extract_material_signals(zf)
        except zipfile.BadZipFile:
            raise HTTPException(400, "повреждённый ZIP")
        finally:
            try:
                tmp.close()
            finally:
                try:
                    os.unlink(tmp_path)
                except FileNotFoundError:
                    pass

    return StreamingResponse(json_iter(), media_type="application/json")

