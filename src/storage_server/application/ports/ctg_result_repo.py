from typing import Protocol, AsyncIterable

from storage_server.domain.ctg_result import CTGResult


class CTGResultRepository(Protocol):

    async def read_by_ctg_id(self, ctg_id: int) -> CTGResult | None: ...

    async def save(self, ctg_id: int, ctg_result: CTGResult) -> None: ...