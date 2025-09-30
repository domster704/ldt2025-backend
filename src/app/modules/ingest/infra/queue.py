import asyncio

from app.modules.ingest.entities.ctg import CardiotocographyPoint

signal_queue: asyncio.Queue[CardiotocographyPoint] = asyncio.Queue()
