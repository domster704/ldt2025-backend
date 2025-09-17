from __future__ import annotations
from typing import NamedTuple
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
)

class DBResources(NamedTuple):
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

def create_db_resources(dsn: str, echo: bool = False) -> DBResources:
    engine = create_async_engine(
        dsn,
        echo=echo,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return DBResources(engine=engine, session_factory=session_factory)
