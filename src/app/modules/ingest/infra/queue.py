import asyncio

from app.modules.ingest.entities.ctg import CardiotocographyPoint

signal_queue: asyncio.Queue[list[CardiotocographyPoint]] = asyncio.Queue(maxsize=20)
