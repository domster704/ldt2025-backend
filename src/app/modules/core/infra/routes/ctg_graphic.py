import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query

from app.common.patient import CurrentPatient
from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.ports.ctg_repository import CTGRepository

router = APIRouter()

@router.get('')
@inject
async def get_ctg_graphic(
    ctg_history_repo: FromDishka[CTGRepository],
    ctg_id: int = Query(..., gt=0),
) -> dict[str, Any]:
    ctg_hist_id = await ctg_history_repo.read(ctg_id)
    if ctg_hist_id is None:
        raise NotFoundObject

    if CurrentPatient.get_dir() is None:
        archive_path = ctg_hist_id.archive_path
        with tempfile.TemporaryDirectory(delete=False) as tmp_dir:
            shutil.unpack_archive(
                filename=archive_path,
                extract_dir=Path(tmp_dir),
            )

        file_path = Path(tmp_dir) / ctg_hist_id.file_path_in_archive
    else:
        file_path = CurrentPatient.get_dir() / ctg_hist_id.file_path_in_archive

    # mock_file_path = Path('').resolve().parent / 'static' / 'mock_graphic.json'
    with open(file_path, mode='r') as f:
        content = f.read()

    CurrentPatient.set_dir(Path(tmp_dir))
    return json.loads(content)
