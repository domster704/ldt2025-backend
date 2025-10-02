import os
from collections.abc import AsyncIterator
from datetime import datetime

import pytz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.modules.ml.domain.entities.process import ProcessResults

db_driver = os.getenv("DB_DRIVER", '')
db_url = os.getenv("DB_DATABASE_NAME", '')

class ResultRepository:
    def __init__(self) -> None:
        self._engine = create_async_engine(db_driver + ":///" + db_url)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=True)

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def add_result(self, ctg_id: int, result: ProcessResults) -> None:
        session = await anext(self.get_session())
        stmt = text(
            """
            INSERT INTO ctg_results (ctg_id, gest_age, bpm, uc, figo, stv, stv_little, acceleration, deceleration, created_at) VALUES 
            (:ctg_id, :gest_age, :bpm, :uc, :figo, :stv, :stv_little, :acceleration, :deceleration, :created_at)
            """
        )
        await session.execute(
            stmt, {
                'ctg_id': ctg_id,
                'gest_age': '38+2 нед',
                'bpm': result.baseline_bpm,
                'uc': result.uterus_mean,
                'figo': result.last_figo,
                'stv': result.stv_all,
                'stv_little': result.stv_10min_mean,
                'acceleration': result.accelerations_count,
                'deceleration': result.decelerations_count,
                'created_at': datetime.now(pytz.timezone('Europe/Moscow')),
            }
        )
        await session.commit()
