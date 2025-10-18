import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter()

@router.get('')
async def get_ctg_graphic(
    ctg_id: int = Query(..., gt=0),
) -> dict[str, Any]:
    mock_file_path = Path('').resolve().parent / 'static' / 'mock_graphic.json'
    with open(mock_file_path, mode='r') as f:
        content = f.read()

    return json.loads(content)