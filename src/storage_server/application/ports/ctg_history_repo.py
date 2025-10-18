from pathlib import Path
from typing import Protocol, AsyncIterable

from ...domain.ctg_history import CTGHistory


class CTGHistoryRepository(Protocol):

    async def read_by_patient_id(self, patient_id: int) -> AsyncIterable[CTGHistory]: ...

    async def save(self, patient_id: int, ctg_history: CTGHistory) -> None: ...

    async def get_archive_path(self, patient_id: int) -> Path: ...