from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class DataclassMixin:

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)