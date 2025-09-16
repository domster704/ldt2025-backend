import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_URL = f'sqlite+aiosqlite:///{os.path.join(BASE_DIR, "database.sqlite")}'

engine = create_async_engine(DB_URL)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=True,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False)


async def init_db():
    import db.models as models
    async with engine.begin() as connection:
        await connection.run_sync(models.SQLModel.metadata.create_all)

if __name__ == '__main__':
    asyncio.run(init_db())
