import datetime

from sqlalchemy import text, bindparam, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.domain.ctg import CTGHistory, CTGResult
from app.modules.core.infra.tables.ctg_history import ctg_history_table
from app.modules.core.usecases.ports.ctg_repository import CTGRepository


class SQLAlchemyCTGRepository(CTGRepository):

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_ctg(self, ctg_ids: list[int]) -> list[CTGHistory]:
        stmt = text(
            """
            SELECT *
            FROM ctg_history
            WHERE ctg_history.id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))

        res = (await self._session.execute(stmt, {"ids": ctg_ids})).all()

        ctg_history = [
            CTGHistory(
                id=row[0],
                file_path_in_archive=row[2],
                archive_path=row[3]
            )
            for row in res
        ]
        return ctg_history

    async def list_results(self, ctg_ids: list[int]) -> list[CTGResult]:
        stmt = text(
            """
            SELECT *
            FROM ctg_results
            WHERE ctg_results.ctg_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))

        res = (await self._session.execute(stmt, {"ids": ctg_ids})).all()
        ctg_results = [
            CTGResult(
                ctg_id=row[1], gest_age=row[2], bpm=row[3], uc=row[4], figo=row[5], figo_prognosis=row[6],
                bhr=row[7], amplitude_oscillations=row[8], oscillation_frequency=row[9], ltv=row[10],
                stv=row[11], stv_little=row[12], accelerations=row[13], deceleration=row[14],
                uterine_contractions=row[15], fetal_movements=row[16], fetal_movements_little=row[17],
                accelerations_little=row[18], deceleration_little=row[19], high_variability=row[20],
                low_variability=row[21], loss_signals=row[22], timestamp=datetime.datetime.fromisoformat(row[23])
            )
            for row in res
        ]
        return ctg_results

    async def add_history(self, ctg_history: CTGHistory, patient_id: int) -> int:
        stmt = text(
            """
            INSERT INTO ctg_history (patient_id, file_path, archive_path)
            VALUES (:patient_id, :file_path, :archive_path) RETURNING id
            """
        )
        id = (await self._session.execute(
            stmt,
            {
                "patient_id": patient_id,
                "file_path": str(ctg_history.file_path_in_archive),
                "archive_path": str(ctg_history.archive_path),
            }
        )).scalar_one()
        await self._session.commit()
        return id

    async def add_histories(self, ctg_history_list: list[CTGHistory], patient_id: int) -> list[int]:
        ids = []
        for ctg_history in ctg_history_list:
            ids.append(await self.add_history(ctg_history, patient_id))

        return ids

    async def read(self, value_id: int) -> CTGHistory | None:
        stmt = (
            select(ctg_history_table)
            .where(ctg_history_table.c.id == value_id)
        )
        res = (await self._session.execute(stmt)).one_or_none()

        if res is None:
            return None

        return CTGHistory.from_db(res._mapping)