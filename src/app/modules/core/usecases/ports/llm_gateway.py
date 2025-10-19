from typing import Protocol


class LLMGateway(Protocol):

    async def get_anamnesis(self, query: str) -> str: ...