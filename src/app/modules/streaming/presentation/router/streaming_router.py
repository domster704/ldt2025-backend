from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.modules.ingest.entities.ctg import CardiotocographyPoint
from app.modules.ingest.infra.queue import signal_queue
from app.modules.streaming.presentation.dto import CardiotocographyPointDTO

streaming_router = APIRouter()


@streaming_router.websocket("")
async def frontend_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            point: CardiotocographyPoint = await signal_queue.get()
            dto = CardiotocographyPointDTO(**asdict(point))
            print(dto)
            await websocket.send_json(dto.model_dump())
    except WebSocketDisconnect:
        pass
