from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Any

from pydantic import BaseModel

from .mixin import DataclassMixin


@dataclass(frozen=True, slots=True)
class CTGHistory(DataclassMixin):
    id: int | None
    file_path_in_archive: Path
    archive_path: Path

    @staticmethod
    def from_db_row(row: Mapping[str, Any]) -> 'CTGHistory':
        return CTGHistory(**row)

    @staticmethod
    def from_dto(model: BaseModel) -> 'CTGHistory':
        data = model.model_dump()
        return CTGHistory(
            id = data.get("id"),
            file_path_in_archive = data.get("file_path_in_archive"),
            archive_path = data.get("archive_path"),
        )
