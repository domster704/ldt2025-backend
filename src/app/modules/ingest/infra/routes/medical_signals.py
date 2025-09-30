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
PROCESS_WINDOW_SEC = 3.0
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


def run_algorithm(last3: list[Sample]) -> dict:
    """
    Ресемплинг последних 3 секунд и возврат ровно последней секунды
    для обеих компонент (bpm, uterus) на равномерной сетке fs=6 Гц.

    Поведение эквивалентно StreamResampler:
      - равномерная сетка на всём окне (3 сек)
      - затирание больших пропусков (> 3.0 сек) как разрывов
      - линейная интерполяция пропусков; края заполняются ближайшим значением
      - возврат только последней секунды (полуинтервал [floor(t1-1), floor(t1-1)+1))
    """
    if not last3:
        return {}

    # параметры ресемплера
    fs = 6.0
    gap_sec = 3.0
    buffer_sec = 3.0  # соответствует входу last3

    # Подготовка исходных массивов времени и значений
    # Уже гарантированно содержат только последние 3 секунды
    times = [s.ts for s in last3]
    if len(times) < 2:
        return {}
    # Сортировка на всякий случай по времени
    paired = sorted(((s.ts, s.bpm, s.uterus) for s in last3), key=lambda x: x[0])
    t = [p[0] for p in paired]
    bpm_vals = [p[1] for p in paired]
    uter_vals = [p[2] for p in paired]

    t0, t1 = t[0], t[-1]
    if math.floor(t1) - math.floor(t0) < buffer_sec:
        # окно ещё меньше 3 секунд – ждём
        return {}

    # Равномерная сетка для всего окна [t0, t1) шаг 1/fs
    step = 1.0 / fs
    tt: list[float] = []
    cur = t0
    # Избегаем накопления ошибок float: ограничим верхнюю границу t1 - epsilon
    # но нам нужно покрыть почти весь полуинтервал до t1
    while cur < t1 - 1e-9:
        tt.append(cur)
        cur += step

    # Линейная интерполяция по известным точкам (аналог np.interp с NaN снаружи)
    def interp_series(t_known: list[float], v_known: list[float], t_query: list[float]) -> list[Optional[float]]:
        res: list[Optional[float]] = []
        n = len(t_known)
        i = 0
        for tq in t_query:
            # продвигаем левый индекс до сегмента, где t[i] <= tq <= t[i+1]
            while i + 1 < n and t_known[i + 1] < tq:
                i += 1
            if tq < t_known[0] or tq > t_known[-1]:
                res.append(None)
            elif i + 1 < n and t_known[i] <= tq <= t_known[i + 1]:
                x0, y0 = t_known[i], v_known[i]
                x1, y1 = t_known[i + 1], v_known[i + 1]
                if x1 == x0:
                    res.append(float(y0))
                else:
                    w = (tq - x0) / (x1 - x0)
                    res.append(float(y0 + (y1 - y0) * w))
            else:
                # точка совпадает с правой границей последнего сегмента
                res.append(float(v_known[-1]))
        return res

    vv_bpm = interp_series(t, bpm_vals, tt)
    vv_uter = interp_series(t, uter_vals, tt)

    # Затираем большие пропуски: точки между t[i] и t[i+1], если разрыв > gap_sec
    gaps = [t[i + 1] - t[i] for i in range(len(t) - 1)]
    for i, g in enumerate(gaps):
        if g > gap_sec:
            left, right = t[i], t[i + 1]
            for idx, tq in enumerate(tt):
                if left < tq < right:
                    vv_bpm[idx] = None
                    vv_uter[idx] = None

    # Интерполяция пропусков и заполнение по краям ближайшими значениями
    def fill_gaps(values: list[Optional[float]]) -> list[float]:
        n = len(values)
        if n == 0:
            return []
        # Найти ближайшие слева/справа валидные значения для каждого индекса
        left_idx = [-1] * n
        last = -1
        for i in range(n):
            if values[i] is not None:
                last = i
            left_idx[i] = last
        right_idx = [-1] * n
        last = -1
        for i in range(n - 1, -1, -1):
            if values[i] is not None:
                last = i
            right_idx[i] = last

        out: list[float] = [0.0] * n
        for i in range(n):
            v = values[i]
            if v is not None:
                out[i] = float(v)
                continue
            li = left_idx[i]
            ri = right_idx[i]
            if li != -1 and ri != -1 and li != ri:
                # линейная интерполяция между двумя опорными точками
                x0, y0 = tt[li], float(values[li])  # type: ignore[arg-type]
                x1, y1 = tt[ri], float(values[ri])  # type: ignore[arg-type]
                if x1 == x0:
                    out[i] = y0
                else:
                    w = (tt[i] - x0) / (x1 - x0)
                    out[i] = y0 + (y1 - y0) * w
            elif li != -1:
                out[i] = float(values[li])  # ближайшее слева
            elif ri != -1:
                out[i] = float(values[ri])  # ближайшее справа
            else:
                out[i] = 0.0
        return out

    vvf_bpm = fill_gaps(vv_bpm)
    vvf_uter = fill_gaps(vv_uter)

    # Оставляем только последнюю секунду
    last_start = math.floor(t1 - 1.0)
    last_end = last_start + 1.0
    mask_idx: list[int] = [i for i, tq in enumerate(tt) if (tq >= last_start and tq < last_end)]

    t_last = [tt[i] for i in mask_idx]
    bpm_raw_last = [vv_bpm[i] if vv_bpm[i] is not None else None for i in mask_idx]
    bpm_filled_last = [vvf_bpm[i] for i in mask_idx]
    uter_raw_last = [vv_uter[i] if vv_uter[i] is not None else None for i in mask_idx]
    uter_filled_last = [vvf_uter[i] for i in mask_idx]

    return {
        "fs": fs,
        "t": t_last,
        "bpm_raw": bpm_raw_last,
        "bpm": bpm_filled_last,
        "uterus_raw": uter_raw_last,
        "uterus": uter_filled_last,
        "samples_3s": len(last3),
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
    next_tick = start_monotonic + PROCESS_WINDOW_SEC
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
            last3, last1 = _split_last_second(window, current_ts)

            alg_out = run_algorithm(last3)

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