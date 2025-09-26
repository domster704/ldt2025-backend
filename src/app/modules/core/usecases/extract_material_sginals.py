import csv
import io
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from zipfile import ZipFile

from fastapi import HTTPException


@dataclass(frozen=True, slots=True)
class DataPoint:
    time_sec: int
    value: Decimal


@dataclass(slots=True)
class ExtractSignals:
    id: str
    bpm: list[DataPoint]  # Частота сердечных сокращений
    uc: list[DataPoint]  # Маточные сокращения


def parse_idx(stem: str) -> tuple[int, int]:
    if (r_i := stem.rfind('_')) != -1:
        l_res = stem[:r_i].strip().split('-')
        if len(l_res) != 2:
            raise ValueError('Uncorrected filename')
        return int(l_res[0]), int(l_res[1])
    raise ValueError('Uncorrected filename')


def extract_material_signals(data: ZipFile) -> dict[str, Any]:
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

    sig_id = entries[0][3].rsplit("_", 1)[0]
    entries.sort(key=lambda x: x[1])

    def load_series(kind: str) -> list[dict[str, Any]]:
        offset = 0
        series: list[dict[str, Any]] = []
        for typ, _, info, _ in filter(lambda e: e[0] == kind, entries):
            with data.open(info, "r") as file_bin:
                reader = csv.reader(io.TextIOWrapper(file_bin, encoding="utf-8", newline=""))
                header = next(reader, None)
                if not header:
                    continue

                time_column = None
                value_column = None
                for i, h in enumerate(header):
                    h = h.strip().lower()
                    if h in ("time_sec", "time"):
                        time_column = i
                    elif h == "value":
                        value_column = i
                if time_column is None or value_column is None:
                    continue

                min_t, max_t = None, None
                for row in reader:
                    try:
                        t = int(float(row[time_column].replace(",", ".")) * 1000)
                        v = float(row[value_column].replace(",", "."))
                    except Exception:
                        continue

                    if min_t is None or t < min_t:
                        min_t = t
                    if max_t is None or t > max_t:
                        max_t = t

                    series.append({"time_sec": t + offset, "value": v})
                if max_t is not None:
                    offset += (max_t - (min_t or 0))
        return series

    return {
        "id": sig_id,
        "bpm": load_series("bpm"),
        "uc": load_series("uc"),
    }
