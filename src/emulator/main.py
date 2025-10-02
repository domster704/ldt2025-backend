import asyncio
import json
import os
import tempfile
from decimal import Decimal

from fastapi import FastAPI, UploadFile, File
import uvicorn
import websockets

from emulator.sending_signals import sending_signals

app = FastAPI()
@app.post("/start")
async def start(archive: UploadFile = File(...)):
    content = await archive.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    async with websockets.connect('ws://127.0.0.1:8010/ws/ingest/input-signal') as ws:
        prev_timestamp = Decimal(0)
        for body, offset in sending_signals(
            tmp_path
        ):
            await asyncio.sleep(float(Decimal(body['timestamp']) - prev_timestamp))
            await ws.send(json.dumps(body))
            prev_timestamp = Decimal(body['timestamp'])
        await ws.send(json.dumps({'type': 'end'}))

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))