from pathlib import Path

from storage_server.application.exceptions.application import UnexpectedError
from storage_server.application.ports.ctg_history_repo import CTGHistoryRepository


async def get_ctg_graphic_archive_path(patient_id: int, ctg_history_repo: CTGHistoryRepository) -> Path:
    try:
        archive_path = await ctg_history_repo.get_archive_path(patient_id)
    except Exception:
        raise UnexpectedError

    return archive_path