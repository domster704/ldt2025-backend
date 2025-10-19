from pathlib import Path


class CurrentPatient:
    _id: int | None = None
    _dir_path: Path | None = None

    # Использовать ТОЛЬКО в ручке /patients/{patient_id}
    @classmethod
    def set_id(cls, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError("ID should be an integer")
        cls._id = value

    @classmethod
    def get_id(cls) -> int:
        if cls._id is None:
            raise RuntimeError("ID does not exist")
        return cls._id

    @classmethod
    def is_empty(cls) -> bool:
        return cls._id is None

    @classmethod
    def set_dir(cls, dir_path: Path) -> None:
        if not isinstance(dir_path, Path):
            raise ValueError("dir_path should be a string")
        cls._dir_path = dir_path

    @classmethod
    def get_dir(cls) -> Path | None:
        return cls._dir_path