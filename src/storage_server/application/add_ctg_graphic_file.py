import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .dto.ctg_graphic_file import CTGGraphicFileAddInDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_history_repo import CTGHistoryRepository
from ..domain.ctg_graphic_archive import CTGGraphicArchive
from ..domain.ctg_history import CTGHistory

@contextmanager
def _new_temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

def _move_file(src: Path, dst: Path) -> None:
    shutil.move(src, dst)

async def add_ctg_graphic_file(
        graphic_file_dto: CTGGraphicFileAddInDTO,
        ctg_history_repo: CTGHistoryRepository, archive_base_dir: Path
) -> None:
    archive_path = archive_base_dir / str(graphic_file_dto.patient_id) / '.zip'
    archive = CTGGraphicArchive(archive_path)
    if archive_path.exists():
        try:
            async with archive.unarchive() as dir_path:
                _move_file(graphic_file_dto.ctg_graphic_file_path, dir_path)
                new_archive = CTGGraphicArchive.archive(dir_path, archive_path)
        except Exception:
            raise UnexpectedError
    else:
        with _new_temp_dir() as temp_dir:
            _move_file(graphic_file_dto.ctg_graphic_file_path, temp_dir)
            new_archive = CTGGraphicArchive.archive(temp_dir, archive_path)

    ctg_history = CTGHistory(
        id=None,
        file_path_in_archive=Path(graphic_file_dto.ctg_graphic_file_path.name),
        archive_path=new_archive.archive_path,
    )
    try:
        await ctg_history_repo.save(graphic_file_dto.patient_id, ctg_history)
    except Exception:
        raise UnexpectedError
