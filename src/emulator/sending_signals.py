import csv
import itertools
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from os import PathLike
from pathlib import Path
from zipfile import ZipFile


@contextmanager
def extract_folder_from_archive(archive_path: Path) -> Path:
    tmpdir = Path(tempfile.mkdtemp())
    try:
        if archive_path.suffix != '.zip':
            raise RuntimeError('Archive must be .zip format')
        with ZipFile(archive_path, 'r') as zf:
            zf.extractall(tmpdir)
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
        root_dir: str | None = None
) -> Iterator[dict, Decimal]:
    path = Path(archive_path)
    with extract_folder_from_archive(path) as tmpdir:
        root = Path(tmpdir)
        bpm_file_iter = file_iter(root / "bpm")
        uterus_file_iter = file_iter(root / "uterus")
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
