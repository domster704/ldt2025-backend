from typing import Protocol

from app.modules.core.domain.ctg import CTGHistory, CTGResult


class CTGRepository(Protocol):

    async def list_ctg(self, ctg_ids: list[int]) -> list[CTGHistory]: ...

    async def list_results(self, ctg_ids: list[int]) -> list[CTGResult]: ...

    async def add_history(self, ctg_history: CTGHistory, patient_id: int) -> int: ...

    async def add_histories(self, ctg_history_list: list[CTGHistory], patient_id: int) -> list[int]: ...
