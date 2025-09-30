import asyncio
import csv
import itertools
import json
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from os import PathLike
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

import websockets


@contextmanager
def extract_folder_from_archive(
        archive_path: Path,
        target_path: PathLike[str],
) -> Path:
    tmpdir = Path(tempfile.mkdtemp())

    try:
        if archive_path.suffix != '.zip':
            raise RuntimeError('Archive must be .zip format')

        with ZipFile(archive_path, 'r') as zf:
            for zi in zf.infolist():
                if str(target_path) + '/' in zi.filename and not zi.is_dir():
                    rel = Path(zi.filename).relative_to(target_path)
                    dst_path = tmpdir / target_path / rel
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(zi) as src, open(dst_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def sort_key(p: Path) -> tuple[datetime, int]:
    filename = p.stem[:p.stem.rfind('_')]
    parts = filename.split("-")
    date = datetime.strptime(parts[0], "%Y%m%d")
    id_ = int(parts[1])
    return date, id_

def file_iter(folder: Path) -> Iterator[Path]:
    files = [p for p in folder.iterdir()]
    sorted_files = sorted(files, key=sort_key)
    for file in sorted_files:
        print(f"{file} is being read...")
        yield file
        print(f"{file} has been read successfully.")

def csv_row_iter(file: Path) -> Iterator[tuple[Decimal, Decimal]]:
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            try:
                yield Decimal(row[0]).quantize(Decimal('0.000001')), Decimal(row[1]).quantize(Decimal('0.000001'))
            except Exception as e:
                continue

def sending_signals(
        archive_path: PathLike,
        checkup_type: Literal["hypoxia", "regular"],
        patient_id: int,
        root_dir: str | None = None
) -> Iterator[dict, Decimal]:
    path = Path(archive_path)
    target_folder = Path(root_dir) / checkup_type / str(patient_id)
    with extract_folder_from_archive(path, target_folder) as tmpdir:
        root = Path(tmpdir)
        bpm_file_iter = file_iter(root / target_folder / "bpm")
        uterus_file_iter = file_iter(root / target_folder / "uterus")
        bpm_offset_timestamp, uterus_offset_timestamp = Decimal(0), Decimal(0)

        bpm_file: Path | None = next(bpm_file_iter, None)
        uterus_file: Path | None = next(uterus_file_iter, None)
        while bpm_file or uterus_file:

            bpm_row_iter = csv_row_iter(bpm_file) if bpm_file else itertools.repeat(None)
            uterus_row_iter = csv_row_iter(uterus_file) if uterus_file else itertools.repeat(None)

            bpm_row: tuple[Decimal, Decimal] | None = next(bpm_row_iter, None)
            uterus_row: tuple[Decimal, Decimal] | None = next(uterus_row_iter, None)

            prev_bpm_timestamp, prev_uterus_timestamp = Decimal(0), Decimal(0)
            while bpm_row or uterus_row:
                if not bpm_row:
                    yield {
                        'type': 'signal',
                        'timestamp': str(uterus_offset_timestamp + uterus_row[0]),
                        'bpm': None,
                        'uterus': str(uterus_row[1])
                    }, uterus_offset_timestamp
                    prev_uterus_timestamp = uterus_row[0]
                    uterus_row = next(uterus_row_iter, None)
                elif not uterus_row:
                    yield {
                        'type': 'signal',
                        'timestamp': str(bpm_offset_timestamp + bpm_row[0]),
                        'bpm': str(bpm_row[1]),
                        'uterus': None
                    }, bpm_offset_timestamp
                    prev_bpm_timestamp = bpm_row[0]
                    bpm_row = next(bpm_row_iter, None)
                elif bpm_offset_timestamp + bpm_row[0] < uterus_offset_timestamp + uterus_row[0]:
                    yield {
                        'type': 'signal',
                        'timestamp': str(bpm_offset_timestamp + bpm_row[0]),
                        'bpm': str(bpm_row[1]),
                        'uterus': None
                    }, bpm_offset_timestamp
                    prev_bpm_timestamp = bpm_row[0]
                    bpm_row = next(bpm_row_iter, None)
                elif bpm_offset_timestamp + bpm_row[0] > uterus_offset_timestamp + uterus_row[0]:
                    yield {
                        'type': 'signal',
                        'timestamp': str(uterus_offset_timestamp + uterus_row[0]),
                        'bpm': None,
                        'uterus': str(uterus_row[1])
                    }, uterus_offset_timestamp
                    prev_uterus_timestamp = uterus_row[0]
                    uterus_row = next(uterus_row_iter, None)
                elif bpm_offset_timestamp + bpm_row[0] == uterus_offset_timestamp + uterus_row[0]:
                    yield {
                        'type': 'signal',
                        'timestamp': str(uterus_offset_timestamp + uterus_row[0]),
                        'bpm': str(bpm_row[1]),
                        'uterus': str(uterus_row[1])
                    }, uterus_offset_timestamp
                    prev_uterus_timestamp = uterus_row[0]
                    prev_bpm_timestamp = bpm_row[0]
                    uterus_row = next(uterus_row_iter, None)
                    bpm_row = next(bpm_row_iter, None)
            bpm_offset_timestamp += prev_bpm_timestamp + Decimal('0.1')
            uterus_offset_timestamp += prev_uterus_timestamp + Decimal('0.1')
            bpm_file: Path | None = next(bpm_file_iter, None)
            uterus_file: Path | None = next(uterus_file_iter, None)


async def main():
    async with websockets.connect('ws://localhost:8010/ws/ingest/input_signal') as ws:
        prev_timestamp = Decimal(0)
        for body, offset in sending_signals(
            Path(__file__).parent / 'static' / 'dataset.zip',
            'hypoxia',
            patient_id=1,
            root_dir='ЛЦТ "НПП "ИТЭЛМА"'
        ):
            await asyncio.sleep(float(Decimal(body['timestamp']) - prev_timestamp))
            await ws.send(json.dumps(body))
            prev_timestamp = Decimal(body['timestamp'])
        await ws.send(json.dumps({'type': 'end'}))

# def main():
#     with open("out.csv", "w", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerow(['timestamp', 'bpm', 'uterus'])
#         i = 0
#         for body, offset in sending_signals(
#             Path(__file__).parent / 'static' / 'dataset.zip',
#             'hypoxia',
#             patient_id=1,
#             root_dir='ЛЦТ "НПП "ИТЭЛМА"'
#         ):
#             writer.writerow([body['timestamp'], body['bpm'], body['uterus']])
#             i += 1


if __name__ == '__main__':
    asyncio.run(main())