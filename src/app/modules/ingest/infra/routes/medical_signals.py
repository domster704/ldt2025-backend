import asyncio
import contextlib
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

import aiohttp
import math
from fastapi import APIRouter
import orjson
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

router = APIRouter()

OUTBOUND_WS_URL = "ws://localhost:9000/ws/outbound"
PROCESS_WINDOW_SEC = 1.0
TICK_SEC = 1.0
import os
RESULTS_SINK = os.getenv("INGEST_RESULTS_SINK", "console").lower()  # "ws" | "console"


class OutboundWSClient:
    """Minimal auto-reconnecting client for outbound ML server."""

    def __init__(self, url: str, *, heartbeat: int = 20) -> None:
        self._url = url
        self._heartbeat = heartbeat
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connect_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def connect(self) -> None:
        async with self._connect_lock:
            if self.is_connected:
                return
            session = await self._ensure_session()
            try:
                self._ws = await session.ws_connect(self._url, heartbeat=self._heartbeat, autoping=True)
            except Exception:
                self._ws = None

    async def ensure_connected(self) -> None:
        if self.is_connected:
            return
        await self.connect()

    async def send_json(self, payload: dict) -> None:
        # Best effort send: try once, if not connected attempt reconnect and retry once
        if not self.is_connected:
            await self.connect()
        if not self.is_connected:
            return
        assert self._ws is not None
        try:
            await self._ws.send_str(_json_dumps(payload))
        except Exception:
            # try one reconnect and resend
            await self.connect()
            if self.is_connected and self._ws is not None and not self._ws.closed:
                with contextlib.suppress(Exception):
                    await self._ws.send_str(_json_dumps(payload))

    async def close(self) -> None:
        if self._ws is not None and not self._ws.closed:
            with contextlib.suppress(Exception):
                await self._ws.close()
        if self._session is not None and not self._session.closed:
            with contextlib.suppress(Exception):
                await self._session.close()

@dataclass
class Sample:
    ts: float
    bpm: float
    uterus: float


def _json_dumps(obj) -> str:
    return orjson.dumps(obj).decode()


def _prune_window(win: Deque[Sample], now_ts: float, span: float) -> None:
    bound = now_ts - span
    while win and win[0].ts < bound:
        win.popleft()


def _split_last_second(win: Deque[Sample], now_ts: float) -> tuple[list[Sample], list[Sample]]:
    """
    Возвращает (last3sec_samples, last1sec_samples) относительно now_ts.
    """
    last3: list[Sample] = []
    last1: list[Sample] = []
    low3 = now_ts - PROCESS_WINDOW_SEC
    low1 = now_ts - 1.0
    for s in win:
        if s.ts >= low3:
            last3.append(s)
            if s.ts >= low1:
                last1.append(s)
    return last3, last1


def _median(nums: list[float]) -> float | None:
    if not nums:
        return None
    s = sorted(nums)
    n = len(s)
    m = n // 2
    if n % 2:
        return float(s[m])
    return (s[m - 1] + s[m]) / 2.0


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


def _parse_signal(msg: dict) -> Optional[Sample]:
    if not isinstance(msg, dict):
        return None
    ts = _safe_float(msg.get("timestamp"))
    bpm = _safe_float(msg.get("bpm"))
    uterus = _safe_float(msg.get("uterus"))
    if ts is None or bpm is None or uterus is None:
        return None
    # Basic sanity limits to drop obvious outliers/noise
    if not (0 <= bpm <= 250):
        return None
    if not (0 <= uterus <= 300):
        return None
    return Sample(ts=ts, bpm=bpm, uterus=uterus)


def run_algorithm(last1sec: list[Sample]) -> dict:
    if not last1sec:
        return {}

    # сортируем по времени
    points = sorted(last1sec, key=lambda s: s.ts)
    max_ts = points[-1].ts
    second_start = math.floor(max_ts - 1.0)
    second_end = second_start + 1.0
    fs = 5.0
    step = 1.0 / fs
    ts_target: list[float] = []
    cur = second_start
    while cur < second_end - 1e-9:
        ts_target.append(cur)
        cur += step

    def compute_stream(values_extractor) -> tuple[list[Optional[float]], Optional[float]]:
        # отбираем точки в текущей секунде
        t_in: list[float] = []
        v_in: list[float] = []
        for s in points:
            if s.ts >= second_start and s.ts < second_end:
                t_in.append(s.ts)
                v_in.append(float(values_extractor(s)))

        # последнее известное значение до секунды
        last_before_val: Optional[float] = None
        for s in points:
            if s.ts < second_start:
                last_before_val = float(values_extractor(s))
            else:
                break

        if t_in:
            # интерполяция с удержанием краёв ближайшим значением
            res: list[Optional[float]] = []
            n = len(t_in)
            i = 0
            for tq in ts_target:
                while i + 1 < n and t_in[i + 1] < tq:
                    i += 1
                if tq < t_in[0]:
                    res.append(float(v_in[0]))
                elif tq > t_in[-1]:
                    res.append(float(v_in[-1]))
                elif i + 1 < n and t_in[i] <= tq <= t_in[i + 1]:
                    x0, y0 = t_in[i], v_in[i]
                    x1, y1 = t_in[i + 1], v_in[i + 1]
                    if x1 == x0:
                        res.append(float(y0))
                    else:
                        w = (tq - x0) / (x1 - x0)
                        res.append(float(y0 + (y1 - y0) * w))
                else:
                    res.append(float(v_in[-1]))
            last_value = None if not res else float(res[-1])
            return res, last_value
        else:
            if last_before_val is not None:
                return [last_before_val for _ in ts_target], last_before_val
            return [None for _ in ts_target], None

    bpm_vals, bpm_last = compute_stream(lambda s: s.bpm)
    uterus_vals, uterus_last = compute_stream(lambda s: s.uterus)

    return {
        "fs": fs,
        "t": ts_target,
        "bpm": bpm_vals,
        "uterus": uterus_vals,
        "bpm_last_value": bpm_last,
        "uterus_last_value": uterus_last,
    }


async def forwarder(out_client: Optional[OutboundWSClient], payload: dict) -> None:
    """
    Без зависимостей от состояния приложения – используем авто-реконнект клиента.
    """
    if RESULTS_SINK == "console":
        print(_json_dumps(payload))
        return
    if out_client is None:
        return
    await out_client.send_json(payload)


async def processing_loop(
    window: Deque[Sample],
    start_monotonic: float,
    out_client: Optional[OutboundWSClient],
    first_signal_wall: float,
):
    """
    Периодический тикер:
    - первый запуск через 3 сек с момента первого сигнала (по монотоних часам),
    - далее каждые 1 сек.
    """
    # Обрабатываем каждую секунду без стартовой задержки на 3 секунды
    next_tick = start_monotonic + TICK_SEC
    now = asyncio.get_running_loop().time()
    if now < next_tick:
        await asyncio.sleep(next_tick - now)

    while True:
        try:
            if window:
                current_ts = max(s.ts for s in window)
            else:
                current_ts = first_signal_wall + (asyncio.get_running_loop().time() - start_monotonic)

            _prune_window(window, current_ts, PROCESS_WINDOW_SEC)
            _last3_unused, last1 = _split_last_second(window, current_ts)

            # Алгоритм работает по последней секунде
            alg_out = run_algorithm(last1)

            # сначала сеть (real-time важнее всего)
            out_payload = {
                "type": "result",
                "timestamp": current_ts,
                "second_range": [current_ts - 1.0, current_ts],
                "count_last_sec": len(last1),
                "algo": alg_out,
            }
            await forwarder(out_client, out_payload)

            await asyncio.sleep(TICK_SEC)
        except asyncio.CancelledError:
            break


@router.websocket("/input_signal")
async def ingest_medical_signals(websocket: WebSocket):
    """Получение сигналов с аппарата"""
    await websocket.accept()
    window: Deque[Sample] = deque()
    processing_task: asyncio.Task | None = None
    out_client: Optional[OutboundWSClient] = None
    try:
        if RESULTS_SINK == "ws":
            out_client = OutboundWSClient(OUTBOUND_WS_URL, heartbeat=20)
            await out_client.connect()
        loop = asyncio.get_running_loop()
        first_signal_wall: float | None = None
        start_monotonic: float | None = None

        while True:
            raw = await websocket.receive_text()
            try:
                msg = orjson.loads(raw)
            except Exception:
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

            sample = _parse_signal(msg)
            if sample is None:
                continue
            ts = sample.ts

            if first_signal_wall is None:
                first_signal_wall = ts
                start_monotonic = loop.time()
                processing_task = asyncio.create_task(
                    processing_loop(window, start_monotonic, out_client, first_signal_wall)
                )

            window.append(sample)
            _prune_window(window, ts, PROCESS_WINDOW_SEC)

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