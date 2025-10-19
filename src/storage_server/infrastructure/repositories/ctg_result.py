from typing import override, AsyncIterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from storage_server.application.ports.ctg_result_repo import CTGResultRepository
from storage_server.domain.ctg_result import CTGResult
from ..tables.ctg_result import ctg_results_table


class SQLAlchemyCTGResultRepository(CTGResultRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def read_by_ctg_id(self, ctg_id: int) -> CTGResult | None:
        stmt = (
            select(ctg_results_table)
            .where(ctg_results_table.c.ctg_id == ctg_id)
        )

        result = await self._session.execute(stmt)

        db_row = result.one_or_none()
        if db_row is None:
            return None

        ctg_result = CTGResult.from_db(db_row._mapping)
        return ctg_result

    @override
    async def save(self, ctg_id: int, ctg_result: CTGResult) -> None:
        ctg_result_dict = ctg_result.to_dict()
        ctg_result_dict.pop("ctg_id")

        stmt = (
            insert(ctg_results_table)
            .values({"ctg_id": ctg_id, **ctg_result_dict})
        )
        await self._session.execute(stmt)
        await self._session.commit()