from dataclasses import asdict, dataclass
from typing import Any

@dataclass
class ToDictMixin:

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)