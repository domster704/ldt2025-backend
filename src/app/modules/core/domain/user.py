from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    id: int
    fio: str