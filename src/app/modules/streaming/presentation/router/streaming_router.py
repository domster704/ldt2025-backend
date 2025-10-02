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


@streaming_router.websocket("/")
async def frontend_ws(
        websocket: WebSocket,
        get_fetal_monitoring_handler: FetalMonitoringHandler = Depends(get_fetal_monitoring_handler)
):
    await websocket.accept()
    try:
        while True:
            points: list[CardiotocographyPoint] = await signal_queue.get()
            print(points)
            ml_res: Process = get_fetal_monitoring_handler.process_stream(points)
            process_dto = ProcessDTO.model_validate(asdict(ml_res))

            for point in points:
                dto = CardiotocographyPointDTO(**asdict(point))
                await websocket.send_json({
                    **dto.model_dump(),
                    "process": process_dto.model_dump()
                })
    except WebSocketDisconnect:
        pass
