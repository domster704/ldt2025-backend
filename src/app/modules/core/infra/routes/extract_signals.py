import os
import tempfile
import zipfile

from fastapi import APIRouter, UploadFile, HTTPException, File
from starlette import status

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

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = tmp.name
    while True:
        chunk = await archive.read(1024 * 1024)
        if not chunk:
            break
        tmp.write(chunk)
    tmp.flush()
    tmp.seek(0)

    try:
        with zipfile.ZipFile(tmp) as zip_file:
            data = extract_material_signals(zip_file)
            return data
    except zipfile.BadZipFile:
        raise HTTPException(400, "повреждённый ZIP")
    finally:
        tmp.close()
        os.unlink(tmp_path)
