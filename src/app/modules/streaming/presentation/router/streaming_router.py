import asyncio
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.params import Depends

from app.modules.ingest.entities.ctg import CardiotocographyPoint
from app.modules.ingest.infra.queue import signal_queue
from app.modules.ml.application.handlers.fetal_monitoring_handler import FetalMonitoringHandler
from app.modules.ml.domain.entities.process import Process
from app.modules.ml.infrastucture.di import get_fetal_monitoring_handler
from app.modules.streaming.presentation.dto import CardiotocographyPointDTO, ProcessDTO

streaming_router = APIRouter()


async def clear_queue(q: asyncio.Queue):
    while not q.empty():
        try:
            q.get_nowait()
        except Exception:
            break


@streaming_router.websocket("/")
async def frontend_ws(
        websocket: WebSocket,
        get_fetal_monitoring_handler: FetalMonitoringHandler = Depends(get_fetal_monitoring_handler)
):
    await websocket.accept()
    await clear_queue(signal_queue)
    try:
        while True:
            points: list[CardiotocographyPoint] = await signal_queue.get()
            if points == [{'type': 'end'}]:
                await get_fetal_monitoring_handler.finalize()
                break

            ml_res: Process = get_fetal_monitoring_handler.process_stream(points)
            process_dto = ProcessDTO.model_validate(asdict(ml_res))

            await websocket.send_json({
                "points": [CardiotocographyPointDTO(**asdict(p)).model_dump() for p in points],
                "process": process_dto.model_dump()
            })
    except WebSocketDisconnect:
        pass
