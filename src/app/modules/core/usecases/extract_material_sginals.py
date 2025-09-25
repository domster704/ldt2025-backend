import csv
import io
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from fastapi import HTTPException
from typing import Any
from zipfile import ZipFile


@dataclass(frozen=True, slots=True)
class DataPoint:
    time_sec: int
    value: Decimal

@dataclass(slots=True)
class ExtractSignals:
    id: str
    bpm: list[DataPoint] # Частота сердечных сокращений
    uc: list[DataPoint] # Маточные сокращения


def parse_idx(stem: str) -> tuple[int, int]:
    if (r_i := stem.rfind('_')) != -1:
        l_res = stem[:r_i].strip().split('-')
        if len(l_res) != 2:
            raise ValueError('Uncorrected filename')
        return int(l_res[0]), int(l_res[1])
    raise ValueError('Uncorrected filename')

def extract_material_signals(data: ZipFile) -> Any:
    """ Извлекает из архива CSV-файлов список ЧСС и МС """
    entries = []
    for info in data.infolist():
        if info.is_dir():
            continue
        path = info.filename.replace("\\", "/")
        if not (path.startswith("bpm/") or path.startswith("uterus/")):
            continue
        typ = "bpm" if path.startswith("bpm/") else "uc"
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        entries.append((typ, parse_idx(stem), info, stem))

    if not entries:
        raise HTTPException(400, "Not found directories bpm/ and uterus/")

    # общий id по первому файлу
    sig_id = entries[0][3].rsplit("_", 1)[0]

    # сортировка по индексу сегмента
    entries.sort(key=lambda x: x[1])

    yield '{"id":' + json.dumps(sig_id) + ',"bpm":['

    def stream_series(kind: str):
        offset = 0
        first_item = True
        for typ, _, info, _ in filter(lambda e: e[0] == kind, entries):
            with data.open(info, "r") as fbin:
                rdr = csv.DictReader(io.TextIOWrapper(fbin, encoding="utf-8", newline=""))
                min_t = None
                max_t = None
                for row in rdr:
                    raw_t = row.get("time_sec") or row.get("time") or "0"
                    raw_v = row.get("value")
                    if raw_v is None:
                        continue

                    # normalize number formats like '0,000000' -> '0.000000'
                    raw_t_s = str(raw_t).strip().replace(",", ".")
                    raw_v_s = str(raw_v).strip().replace(",", ".")

                    try:
                        # floor to whole seconds for continuity across segments
                        t_dec = Decimal(raw_t_s)
                        t = int(t_dec.to_integral_value(rounding=ROUND_FLOOR))
                    except Exception:
                        # skip rows with broken timestamp
                        continue

                    try:
                        v_dec = Decimal(raw_v_s)
                    except Exception:
                        # skip rows with broken value
                        continue

                    if min_t is None or t < min_t:
                        min_t = t
                    if max_t is None or t > max_t:
                        max_t = t

                    t_adj = t + offset
                    item = {"time_sec": t_adj, "value": str(v_dec)}
                    if not first_item:
                        yield ","
                    yield json.dumps(item, ensure_ascii=False)
                    first_item = False
                if max_t is not None:
                    # следующий сегмент начинается после последнего t_adj
                    offset += (max_t - (min_t or 0))

    # bpm
    yield from stream_series("bpm")
    yield '],"uc":['
    # uc
    yield from stream_series("uc")
    yield "]}"