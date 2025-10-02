from datetime import datetime
import os
import atexit
from io import TextIOWrapper
from typing import Callable, Any, Awaitable

from app.modules.core.domain.ctg import CTGHistory
from app.modules.core.infra.provider import get_container
from app.modules.core.usecases.ports.ctg import CTGPort
from app.modules.ingest.entities.ctg import CardiotocographyPoint


async def make_file_logger(log_dir_path: str, patient_id: int | None) -> Callable[[list[Any]], Awaitable[None]]:
    i = 1
    file: TextIOWrapper = None
    base_dir = os.path.join(log_dir_path, str(patient_id)) if patient_id is not None else log_dir_path

    async def open_new_file() -> None:
        nonlocal file, i
        file_name = datetime.now().strftime("%Y_%m_%d_%H%M_") + str(i) + "-ctg-log.csv"
        os.makedirs(base_dir, exist_ok=True)
        file = open(os.path.join(base_dir, file_name), "a", buffering=100)
        if patient_id:
            container = get_container('async')
            async with container() as di:
                ctg_repo = await di.get(CTGPort)
            await ctg_repo.add_history(CTGHistory(
                id=None,
                file_path=os.path.join(base_dir, file_name),
                archive_path=None
            ), patient_id)
        file.write("timestamp,bpm,uc\n")

    def close() -> None:
        nonlocal file
        if file and not file.closed:
            try:
                file.close()
            except Exception:
                pass

    async def write(batch: list[CardiotocographyPoint]) -> None:
        nonlocal i, file
        try:
            for item in batch:
                if item == {"type": "end"}:
                    close()
                    i += 1
                    await open_new_file()
                else:
                    file.write(f"{item.timestamp},{item.bpm},{item.uc}\n")
        except Exception:
            close()
            raise

    await open_new_file()
    atexit.register(close)

    return write