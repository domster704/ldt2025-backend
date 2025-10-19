import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter()

@router.get('')
async def get_ctg_graphic(
    ctg_id: int = Query(..., gt=0),
) -> dict[str, Any]:
    result_dict = {}
    result_dict['result'] = json.loads(json.dumps({
        "gest_age": "string",
        "bpm": 0,
        "uc": 0,
        "figo": "string",
        "figo_prognosis": "string",
        "bhr": 0,
        "amplitude_oscillations": 0,
        "oscillation_frequency": 0,
        "ltv": 0,
        "stv": 0,
        "stv_little": 0,
        "accelerations": 0,
        "decelerations": 0,
        "uterine_contractions": 0,
        "fetal_movements": 0,
        "fetal_movements_little": 0,
        "accelerations_little": 0,
        "deceleration_little": 0,
        "high_variability": 0,
        "low_variability": 0,
        "loss_signals": 0
    }))
    mock_file_path = Path('').resolve().parent / 'static' / 'mock_graphic.json'
    with open(mock_file_path, mode='r') as f:
        content = f.read()

    result_dict['graphic'] = json.loads(content)
    return result_dict