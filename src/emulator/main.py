import asyncio
import json
import os
import tempfile
from decimal import Decimal

import uvicorn
import websockets
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
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


@app.post("/start")
async def start(archive: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    content = await archive.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    background_tasks.add_task(run_emulation, tmp_path)

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
