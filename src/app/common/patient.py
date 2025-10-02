class CurrentPatientID:
    _id: int | None = None

    # Использовать ТОЛЬКО в ручке /patients/{patient_id}
    @classmethod
    def set(cls, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError("ID should be an integer")
        cls._id = value

    @classmethod
    def get(cls) -> int:
        if cls._id is None:
            raise RuntimeError("ID does not exist")
        return cls._id

    @classmethod
    def is_empty(cls) -> bool:
        return cls._id is None