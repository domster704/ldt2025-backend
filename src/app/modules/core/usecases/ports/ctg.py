from typing import Protocol

from app.modules.core.domain.ctg import CTGHistory, CTGResult


class CTGPort(Protocol):

    async def list_ctg(self, ctg_ids: list[int]) -> list[CTGHistory]: ...

    async def list_results(self, ctg_ids: list[int]) -> list[CTGResult]: ...

    async def add_history(self, ctg_history: CTGHistory, patient_id: int) -> None: ...

    async def add_result(self, ctg_result: CTGResult, ctg_id: int) -> None: ...