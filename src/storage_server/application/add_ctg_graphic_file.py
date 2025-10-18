import tempfile
from contextlib import contextmanager
from pathlib import Path

from .dto.ctg_graphic_file import CTGGraphicFileAddInDTO
from .exceptions.application import UnexpectedError
from .ports.ctg_history_repo import CTGHistoryRepository
from ..domain.ctg_graphic_archive import CTGGraphicArchive
from ..domain.ctg_history import CTGHistory

@contextmanager
def new_temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

def write_file(filename: str, content: bytes, dst: Path) -> None:
    with open (dst / filename, mode='wb') as f:
        f.write(content)

async def add_ctg_graphic_file(
        graphic_file_dto: CTGGraphicFileAddInDTO,
        ctg_history_repo: CTGHistoryRepository,
        archive_base_dir: Path
) -> None:
    archive_path = archive_base_dir / (str(graphic_file_dto.patient_id) + '.zip')
    archive = CTGGraphicArchive(archive_path)
    if archive_path.exists():
        try:
            with archive.unarchive() as dir_path:
                write_file(
                    graphic_file_dto.filename,
                    graphic_file_dto.file,
                    dir_path
                )
                new_archive = CTGGraphicArchive.archive(dir_path, archive_path)
        except Exception as err:
            raise UnexpectedError from err
    else:
        with new_temp_dir() as temp_dir:
            write_file(
                graphic_file_dto.filename,
                graphic_file_dto.file,
                temp_dir
            )
            new_archive = CTGGraphicArchive.archive(temp_dir, archive_path)

    ctg_history = CTGHistory(
        id=None,
        file_path_in_archive=graphic_file_dto.filename,
        archive_path=str(new_archive.archive_path),
    )
    try:
        await ctg_history_repo.save(graphic_file_dto.patient_id, ctg_history)
    except Exception as err:
        raise UnexpectedError from err
