from collections.abc import AsyncIterable
from functools import cached_property

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


class DBMixin:
    def __init__(self):
        self._engine = create_async_engine(...)
        self._session_factory = async_sessionmaker(self._engine)

    async def get_session(self) -> AsyncSession:
        async with self._session_factory() as session:
            yield session
