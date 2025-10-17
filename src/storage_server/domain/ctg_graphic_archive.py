import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from storage_server.domain.mixin import DataclassMixin


@dataclass(slots=True, frozen=True)
class CTGGraphicArchive(DataclassMixin):
    archive_path: Path

    @staticmethod
    def archive(dir_path: Path, archive_path: Path) -> 'CTGGraphicArchive':
        shutil.make_archive(
            base_name=str(archive_path),
            format=archive_path.suffix,
            root_dir=str(dir_path)
        )
        return CTGGraphicArchive(archive_path)

    @contextmanager
    def unarchive(self, extract_dir: Path | None = None) -> Path:
        if extract_dir is not None:
            shutil.unpack_archive(
                filename=self.archive_path,
                extract_dir=extract_dir,
                format=self.archive_path.suffix
            )
            yield extract_dir
            shutil.rmtree(extract_dir)
        else:
            with tempfile.TemporaryDirectory() as tmp_dir:
                shutil.unpack_archive(
                    filename=self.archive_path,
                    extract_dir=Path(tmp_dir),
                    format=self.archive_path.suffix
                )
                yield Path(tmp_dir)
