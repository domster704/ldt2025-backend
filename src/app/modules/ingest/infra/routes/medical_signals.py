import asyncio
import contextlib
import datetime
import math
import os
from dataclasses import dataclass
from statistics import mean
from typing import Any

import orjson
from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from app.common.patient import CurrentPatientID
from app.modules.ingest.entities.ctg import CardiotocographyPoint
from app.modules.ingest.infra.file_logger import make_file_logger
from app.modules.ingest.infra.multiplexer import Multiplexer
from app.modules.ingest.infra.queue import signal_queue

router = APIRouter()

RESULTS_SINK = os.getenv("INGEST_RESULTS_SINK", "signal").lower()
FS = 5


def json_dumps(obj: dict[str, Any]) -> str:
    """Сериализует словарь в JSON-строку.

    Args:
        obj (dict[str, Any]): Python-словарь.

    Returns:
        str: JSON-представление объекта.
    """
    return orjson.dumps(obj).decode()


def safe_float(value: Any) -> float | None:
    """Преобразует значение в float с защитой от ошибок.

    Args:
        value (Any): Входное значение.

    Returns:
        float | None: Преобразованное число или None,
        если значение некорректное (NaN, Inf, None, строка с мусором).
    """
    try:
        if value is None:
            return None
        f = float(str(value).strip())
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


@dataclass
class Sample:
    """Один измеренный сэмпл сигнала.

    Attributes:
        ts (float): Временная метка (секунды).
        bpm (float): Значение сердцебиения.
        uterus (float): Значение маточной активности.
    """
    ts: float
    bpm: float
    uterus: float


class SignalProcessor:
    """Обрабатывает входные сигналы, восстанавливает пропущенные значения.

    Поддерживает:
    - Парсинг входных сообщений.
    - Хранение последних известных значений.
    - Усреднение значений внутри секунды.
    - Добивку (padding) до заданного числа выборок fs.
    """

    def __init__(self, fs: int = FS) -> None:
        """Создаёт обработчик сигналов.

        Args:
            fs (int, optional): Количество выборок на секунду. По умолчанию 5.
        """
        self.fs = fs
        self._last_values: dict[str, float | None] = {"bpm": None, "uterus": None}
        self._second_avgs: dict[int, dict[str, float]] = {}

    def parse(self, msg: dict[str, Any]) -> Sample | None:
        """Парсит сообщение и заполняет пропуски последними значениями.

        Args:
            msg (dict[str, Any]): Входное сообщение от клиента.

        Returns:
            Sample | None: Объект Sample или None, если сообщение некорректное.
        """
        ts = safe_float(msg.get("timestamp"))
        bpm = safe_float(msg.get("bpm"))
        uterus = safe_float(msg.get("uterus"))

        if ts is None:
            return None

        sec = int(ts)

        bpm = bpm or self._get_fallback(sec, "bpm")
        uterus = uterus or self._get_fallback(sec, "uterus")

        if bpm is None or uterus is None:
            return None

        sample = Sample(ts=ts, bpm=bpm, uterus=uterus)

        self._last_values.update({"bpm": bpm, "uterus": uterus})
        self._update_second_avg(sec, bpm, uterus)

        return sample

    def _get_fallback(self, sec: int, key: str) -> float | None:
        """Возвращает запасное значение, если текущее отсутствует.

        Args:
            sec (int): Секунда, к которой относится выборка.
            key (str): Имя параметра ("bpm" или "uterus").

        Returns:
            float | None: Последнее известное значение или None.
        """
        if sec in self._second_avgs and self._second_avgs[sec][key] is not None:
            return self._second_avgs[sec][key]
        return self._last_values[key]

    def _update_second_avg(self, sec: int, bpm: float, uterus: float) -> None:
        """Обновляет усреднённые значения для данной секунды.

        Args:
            sec (int): Секунда.
            bpm (float): Сердцебиение.
            uterus (float): Маточная активность.
        """
        if sec not in self._second_avgs:
            self._second_avgs[sec] = {"bpm": bpm, "uterus": uterus}
        else:
            self._second_avgs[sec]["bpm"] = mean([self._second_avgs[sec]["bpm"], bpm])
            self._second_avgs[sec]["uterus"] = mean([self._second_avgs[sec]["uterus"], uterus])

    def pad_samples(self, samples: list[Sample]) -> list[Sample]:
        """Дополняет список до fs выборок усреднением.

        Args:
            samples (list[Sample]): Список сэмплов.

        Returns:
            list[Sample]: Список длиной fs.
        """
        if not samples:
            return []

        mean_bpm = mean(s.bpm for s in samples)
        mean_ut = mean(s.uterus for s in samples)

        result = samples.copy()
        while len(result) < self.fs:
            result.append(Sample(ts=result[-1].ts, bpm=mean_bpm, uterus=mean_ut))
        return result[-self.fs:]


async def forwarder(payload_list: list[CardiotocographyPoint]) -> None:
    """Отправляет данные в консоль или во внешний WebSocket.

    Args:
        payload_list (list[CardiotocographyPoint]): Массив данных для отправки.
    """
    if RESULTS_SINK == "console":
        print(payload_list, datetime.datetime.now())
    elif RESULTS_SINK == "signal":
        await signal_queue.put(payload_list)


async def processing_loop(
        queue: asyncio.Queue[Sample],
        mux: Multiplexer,
        fs: int = FS,
) -> None:
    """Основной цикл обработки сигналов.

    Работает строго раз в секунду (по системному времени), выдаёт fs выборок.
    Если данных нет, повторяет последнее значение.

    Args:
        mux (Multiplexer): Мультиплексор
        queue (asyncio.Queue[Sample]): Очередь входных сэмплов.
        fs (int, optional): Количество выборок на секунду. По умолчанию 5.
    """
    processor = SignalProcessor(fs)
    loop = asyncio.get_running_loop()

    start_mono = loop.time()
    start_ts: int | None = None
    next_tick = start_mono
    tick_index = 0

    last_second_data: list[Sample] = []
    last_value: Sample | None = None

    while True:
        try:
            timeout = max(0, next_tick - loop.time())
            try:
                sample: Sample = await asyncio.wait_for(queue.get(), timeout)
                if start_ts is None:
                    start_ts = int(sample.ts)
                last_second_data.append(sample)
            except asyncio.TimeoutError:
                if start_ts is None:
                    next_tick += 1.0
                    continue

                current_sec = start_ts + tick_index
                tick_index += 1

                data: list[Sample] = processor.pad_samples(last_second_data)
                if not data and last_value:
                    sec_start = float(current_sec)
                    step = 1.0 / fs
                    data = [
                        Sample(ts=sec_start + i * step,
                               bpm=last_value.bpm,
                               uterus=last_value.uterus)
                        for i in range(fs)
                    ]

                if data:
                    payload_list: list[CardiotocographyPoint] = []

                    sec_start = float(current_sec)
                    step = 1.0 / fs
                    for i, s in enumerate(data):
                        payload = CardiotocographyPoint(
                            timestamp=sec_start + i * step,
                            bpm=s.bpm,
                            uc=max(0, s.uterus),
                        )
                        payload_list.append(payload)
                    try:
                        await mux.send(payload_list)
                    except Exception as e:
                        print(e)
                    last_value = data[-1]
                    # print('============')

                last_second_data = []
                next_tick += 1.0

        except asyncio.CancelledError:
            break


@router.websocket("/input-signal")
async def ingest_medical_signals(websocket: WebSocket) -> None:
    """WebSocket-эндпоинт для приёма медицинских сигналов.

    Принимает сообщения вида:
        {"type": "signal", "timestamp": <float>, "bpm": <float>, "uterus": <float>}
        {"type": "end"}  -- завершение сессии.

    Args:
        websocket (WebSocket): WebSocket-соединение от клиента.
    """
    await websocket.accept()
    queue: asyncio.Queue[Sample] = asyncio.Queue()
    processing_task: asyncio.Task | None = None
    processor = SignalProcessor()

    file_logger = await make_file_logger(
        '/tmp/ctg_logs',
        None if CurrentPatientID.is_empty() else CurrentPatientID.get()
    )
    mux = Multiplexer(forwarder, file_logger)

    try:
        processing_task = asyncio.create_task(processing_loop(queue, mux))

        while True:
            raw = await websocket.receive_text()
            try:
                msg = orjson.loads(raw)
            except Exception:
                continue

            if msg.get("type") == "end":
                await mux.send([{"type": "end"}])
                break

            if msg.get("type") != "signal":
                continue

            sample = processor.parse(msg)
            if sample:
                await queue.put(sample)

    except WebSocketDisconnect:
        pass
    finally:
        if processing_task and not processing_task.done():
            processing_task.cancel()
            with contextlib.suppress(Exception):
                await processing_task
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
