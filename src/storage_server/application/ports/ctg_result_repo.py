from typing import Protocol, AsyncIterable

from ...domain.ctg_result import CTGResult


class CTGResultRepository(Protocol):

    async def read_by_ctg_id(self, ctg_id: int) -> AsyncIterable[CTGResult]: ...

    async def save(self, ctg_id: int, cth_history: CTGResult) -> None: ...