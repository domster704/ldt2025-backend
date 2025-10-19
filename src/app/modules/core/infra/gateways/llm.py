from typing import override

from httpx import AsyncClient

from ...usecases.ports.llm_gateway import LLMGateway


class HttpxLLMGateway(LLMGateway):
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    @override
    async def get_anamnesis(self, query: str) -> str:
        resp = await self._client.post(
            '/chat',
            json={"message": query},
        )
        resp.raise_for_status()
        return resp.json()['response']