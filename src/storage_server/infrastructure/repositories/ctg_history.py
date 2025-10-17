from pathlib import Path
from typing import AsyncIterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...application.ports.ctg_history_repo import CTGHistoryRepository
from ...domain.ctg_history import CTGHistory
from ..tables.ctg_history import ctg_history_table


class SQLAlchemyCTGHistoryRepository(CTGHistoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read_by_patient_id(self, patient_id: int) -> AsyncIterable[CTGHistory]:
        stmt = (
            select(ctg_history_table)
            .where(ctg_history_table.c.patient_id == patient_id)
        )

        result = await self._session.execute(stmt)

        rows = result.all()
        for row in rows:
            patient = CTGHistory.from_db_row(row._mapping)
            yield patient

    async def get_archive_path(self, patient_id: int) -> Path:
        stmt = (
            select(ctg_history_table.c.archive_path)
            .where(ctg_history_table.c.patient_id == patient_id)
        )

        result = await self._session.execute(stmt)

        archive_path = Path(result.scalar_one())
        return archive_path

    async def save(self, patient_id: int, ctg_history: CTGHistory) -> None:
        ctg_history_dict = ctg_history.to_dict()
        ctg_history_dict.pop("id")

        stmt = (
            insert(ctg_history_table)
            .values({"id": patient_id, **ctg_history_dict})
        )
        await self._session.execute(stmt)
        await self._session.commit()