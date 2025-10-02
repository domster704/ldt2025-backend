from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.domain.ctg import CTGHistory, CTGResult
from app.modules.core.usecases.ports.ctg import CTGPort


class CTGRepository(CTGPort):

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_ctg(self, ctg_ids: list[int]) -> list[CTGHistory]:
        stmt = text(
            """
            SELECT * FROM ctg_history WHERE id IN :ids
            """
        )
        res = await self._session.execute(stmt, {"ids": tuple(ctg_ids)})
        ctgs = [
            CTGHistory(
                id=row[0],
                file_path=row[2],
                archive_path=row[3]
            )
            for row in res.all()
        ]
        return ctgs

    async def list_results(self, ctg_ids: list[int]) -> list[CTGResult]:
        stmt = text(
            """
            SELECT * FROM ctg_results WHERE ctg_results.ctg_id IN :ids
            """
        )
        res = await self._session.execute(stmt, {"ids": tuple(ctg_ids)})
        ctg_results = [
            CTGResult(
                ctg_id=row[1], gest_age=row[2], bpm=row[3], uc=row[4], figo=row[5], figo_prognosis=row[6],
                bhr=row[7], amplitude_oscillations=row[8], oscillation_frequency=row[9], ltv=row[10],
                stv=row[11], stv_little=row[12], accellations=row[13], deceleration=row[14],
                uterine_contractions=row[15], fetal_movements=row[16], fetal_movements_little=row[17],
                accellations_little=row[18], deceleration_little=row[19], high_variability=row[20],
                low_variability=row[21], loss_signals=row[22], timestamp=row[23]
            )
            for row in res.all()
        ]
        return ctg_results

    async def add_history(self, ctg_history: CTGHistory, patient_id: int) -> None:
        stmt = text(
            """
            INSERT INTO ctg_history (patient_id, file_path, archive_path) VALUES (:patient_id, :file_path, :archive_path)
            """
        )
        await self._session.execute(
            stmt,
            {
                "patient_id": patient_id,
                "file_path": ctg_history.file_path,
                "archive_path": ctg_history.archive_path,
            }
        )
        await self._session.commit()

    async def add_result(self, ctg_result: CTGResult, ctg_id: int) -> None:
        stmt = text(
            """
            INSERT into ctg_results (ctg_id, created_at) 
            """
        )
