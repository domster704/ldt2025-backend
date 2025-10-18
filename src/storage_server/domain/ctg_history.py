from dataclasses import dataclass, fields
from typing import Mapping, Any

from pydantic import BaseModel

from .mixin import DataclassMixin


@dataclass(frozen=True, slots=True)
class CTGHistory(DataclassMixin):
    id: int | None
    file_path_in_archive: str
    archive_path: str

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'CTGHistory':
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}

        return CTGHistory(**filtered)

    @staticmethod
    def from_dto(model: BaseModel) -> 'CTGHistory':
        data = model.model_dump()
        return CTGHistory(
            id = data.get("id"),
            file_path_in_archive = data.get("file_path_in_archive"),
            archive_path = data.get("archive_path"),
        )
