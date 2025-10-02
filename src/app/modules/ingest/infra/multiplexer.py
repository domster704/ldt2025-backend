import asyncio
from typing import Callable, Iterable, Any

SinkFn = Callable[[Iterable[Any]], None]

class Multiplexer:
    def __init__(self, *sinks: SinkFn) -> None:
        self._sinks = sinks
        self._loop = asyncio.get_event_loop()

    async def send(self, batch: Iterable[Any]) -> None:
        tasks = []
        for sink in self._sinks:
            res = sink(batch)
            if asyncio.iscoroutine(res):
                tasks.append(res)  # async sink
        if tasks:
            await asyncio.gather(*tasks)