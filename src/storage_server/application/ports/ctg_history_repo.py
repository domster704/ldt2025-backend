from typing import Protocol, AsyncIterable

from ...domain.ctg_history import CTGHistory


class CTGHistoryRepository(Protocol):

    async def read_by_patient_id(self, patient_id: int) -> AsyncIterable[CTGHistory]: ...

    async def save(self, patient_id: int, cth_history: CTGHistory) -> None: ...