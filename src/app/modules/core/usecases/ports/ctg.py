from typing import Protocol

from app.modules.core.domain.ctg import CTGHistory, CTGResult


class CTGPort(Protocol):

    async def get_by_id(self, ctg_id: int) -> CTGHistory: ...

    async def list(self, ctg_ids: list[int]) -> list[CTGHistory]: ...

    async def get_ctg_result(self, ctg_id: int) -> CTGResult | None: ...