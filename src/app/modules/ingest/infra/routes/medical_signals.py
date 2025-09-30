import asyncio
import contextlib
import datetime
import math
from dataclasses import dataclass
from statistics import mean
from typing import Optional

import aiohttp
import orjson
from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

router = APIRouter()

OUTBOUND_WS_URL = "ws://localhost:9000/ws/outbound"
PROCESS_WINDOW_SEC = 1.0
TICK_SEC = 1.0
import os

RESULTS_SINK = os.getenv("INGEST_RESULTS_SINK", "console").lower()


class OutboundWSClient:
    """Клиент для отправки данных во внешний WebSocket с авто-реконнектом."""

    def __init__(self, url: str, heartbeat: int = 20) -> None:
        self._url = url
        self._heartbeat = heartbeat
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        async with self._lock:
            if self.is_connected:
                return
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            try:
                self._ws = await self._session.ws_connect(
                    self._url, heartbeat=self._heartbeat, autoping=True
                )
            except Exception:
                self._ws = None

    async def send_json(self, payload: dict) -> None:
        """Отправка с одним автоматическим ретраем при разрыве соединения."""
        if not self.is_connected:
            await self.connect()
        if not self.is_connected:
            return
        try:
            assert self._ws is not None
            await self._ws.send_str(_json_dumps(payload))
        except Exception:
            await self.connect()
            if self.is_connected and self._ws is not None:
                with contextlib.suppress(Exception):
                    await self._ws.send_str(_json_dumps(payload))

    async def close(self) -> None:
        if self._ws:
            with contextlib.suppress(Exception):
                await self._ws.close()
        if self._session:
            with contextlib.suppress(Exception):
                await self._session.close()


@dataclass
class Sample:
    ts: float
    bpm: float
    uterus: float


def _json_dumps(obj) -> str:
    return orjson.dumps(obj).decode()


def _safe_float(value) -> Optional[float]:
    try:
        if value is None:
            return None
        f = float(str(value).strip())
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


_last_values: dict[str, float] = {"bpm": None, "uterus": None}
_last_second_avgs: dict[int, dict[str, float]] = {}


def _parse_signal(msg: dict) -> Optional[Sample]:
    if not isinstance(msg, dict):
        return None

    ts = _safe_float(msg.get("timestamp"))
    bpm = _safe_float(msg.get("bpm"))
    uterus = _safe_float(msg.get("uterus"))

    if ts is None:
        return None

    sec = int(ts)

    if bpm is None:
        if sec in _last_second_avgs and _last_second_avgs[sec]["bpm"] is not None:
            bpm = _last_second_avgs[sec]["bpm"]
        elif _last_values["bpm"] is not None:
            bpm = _last_values["bpm"]

    if uterus is None:
        if sec in _last_second_avgs and _last_second_avgs[sec]["uterus"] is not None:
            uterus = _last_second_avgs[sec]["uterus"]
        elif _last_values["uterus"] is not None:
            uterus = _last_values["uterus"]

    if bpm is None or uterus is None:
        return None

    sample = Sample(ts=ts, bpm=bpm, uterus=uterus)

    _last_values["bpm"] = bpm
    _last_values["uterus"] = uterus

    if sec not in _last_second_avgs:
        _last_second_avgs[sec] = {"bpm": bpm, "uterus": uterus}
    else:
        prev_bpm = _last_second_avgs[sec]["bpm"]
        prev_ut = _last_second_avgs[sec]["uterus"]
        _last_second_avgs[sec]["bpm"] = (prev_bpm + bpm) / 2 if prev_bpm is not None else bpm
        _last_second_avgs[sec]["uterus"] = (prev_ut + uterus) / 2 if prev_ut is not None else uterus

    return sample


async def forwarder(out_client, payload: dict) -> None:
    if RESULTS_SINK == "console":
        print(_json_dumps(payload), datetime.datetime.now())
        return
    # if out_client is None:
    #     return
    # await out_client.send_json(payload)
    print('*', payload, datetime.datetime.now())


def pad_samples(samples: list[Sample], fs: int) -> list[Sample]:
    if not samples:
        return []

    mean_bpm = mean(s.bpm for s in samples)
    mean_ut = mean(s.uterus for s in samples)

    result = samples.copy()

    while len(result) < fs:
        ts_val = result[-1].ts if result else 0.0
        result.append(Sample(ts=ts_val, bpm=mean_bpm, uterus=mean_ut))

    if len(result) > fs:
        result = result[-fs:]

    return result


async def processing_loop(
        queue: asyncio.Queue[Sample],
        out_client: Optional["OutboundWSClient"],
        fs: int = 5
):
    """
    Раз в секунду отдаёт одно значение:
    - если были новые сэмплы → берём последний в этой секунде
    - если сэмплов не было → берём последнее известное значение
    timestamp = секунда данных, а не монотоничное время
    """
    loop = asyncio.get_running_loop()
    start_mono = loop.time()
    start_ts: Optional[int] = None

    next_tick = start_mono

    last_second_data: list[Sample] = []
    last_second: int | None = None
    last_value: Optional[Sample] = None

    while True:
        try:
            timeout = max(0, next_tick - loop.time())
            try:
                sample: Sample = await asyncio.wait_for(queue.get(), timeout)
                if last_second is not None and int(sample.ts) > last_second:
                    last_second_data = []

                last_second_data.append(sample)
                last_second = int(sample.ts)

                if start_ts is None:
                    start_ts = int(sample.ts)
            except asyncio.TimeoutError:
                if start_ts is None:
                    next_tick += 1.0
                    continue

                elapsed = int(loop.time() - start_mono)
                current_sec = start_ts + elapsed

                data_with_fs_length = pad_samples(last_second_data, fs)
                if not data_with_fs_length and last_value is not None:
                    sec_start = float(current_sec)
                    step = 1.0 / fs
                    data_with_fs_length = [
                        Sample(ts=sec_start + i * step,
                               bpm=last_value.bpm,
                               uterus=last_value.uterus)
                        for i in range(fs)
                    ]

                if data_with_fs_length:
                    sec_start = float(current_sec)
                    step = 1.0 / fs
                    for i, s in enumerate(data_with_fs_length):
                        payload = {
                            "type": "console",
                            "timestamp": sec_start + i * step,
                            "value": {
                                "bpm": s.bpm,
                                "uterus": s.uterus,
                            },
                        }
                        await forwarder(out_client, payload)
                    last_value = data_with_fs_length[-1]
                    print("======")
                last_second_data = []

                next_tick += 1.0
        except asyncio.CancelledError:
            break


@router.websocket("/input_signal")
async def ingest_medical_signals(websocket: WebSocket):
    await websocket.accept()
    processing_task: asyncio.Task | None = None
    out_client: Optional[OutboundWSClient] = None
    queue: asyncio.Queue[Sample] = asyncio.Queue()

    try:
        if RESULTS_SINK == "ws":
            out_client = OutboundWSClient(OUTBOUND_WS_URL, heartbeat=20)
            await out_client.connect()

        processing_task = asyncio.create_task(processing_loop(queue, out_client))

        while True:
            raw = await websocket.receive_text()
            try:
                msg = orjson.loads(raw)
            except Exception as e:
                continue

            mtype = msg.get("type")
            if mtype == "end":
                if RESULTS_SINK == "console":
                    print(_json_dumps({"type": "end"}))
                elif out_client is not None:
                    await out_client.send_json({"type": "end"})
                break

            if mtype != "signal":
                continue

            sample: Sample | None = _parse_signal(msg)
            if sample is None:
                continue

            await queue.put(sample)

    except WebSocketDisconnect:
        pass
    finally:
        if processing_task and not processing_task.done():
            processing_task.cancel()
            with contextlib.suppress(Exception):
                await processing_task
        if out_client is not None:
            await out_client.close()
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
