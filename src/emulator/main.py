import asyncio
import json
import os
import tempfile
from decimal import Decimal

import uvicorn
import websockets
from fastapi import FastAPI, UploadFile, File
from starlette.middleware.cors import CORSMiddleware

from emulator.sending_signals import sending_signals

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_task: asyncio.Task | None = None


@app.post("/start")
async def start(archive: UploadFile = File(...)):
    global current_task

    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except asyncio.CancelledError:
            print("Предыдущая эмуляция остановлена")

    content = await archive.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    current_task = asyncio.create_task(run_emulation(tmp_path))

    return {"status": "started"}


async def run_emulation(tmp_path: str):
    async with websockets.connect('ws://127.0.0.1:8010/ws/ingest/input-signal') as ws:
        prev_timestamp = Decimal(0)
        for body, offset in sending_signals(tmp_path):
            await asyncio.sleep(float(Decimal(body['timestamp']) - prev_timestamp))
            await ws.send(json.dumps(body))
            prev_timestamp = Decimal(body['timestamp'])
        await ws.send(json.dumps({'type': 'end'}))


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))
