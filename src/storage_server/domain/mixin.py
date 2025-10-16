from typing import Any


class DataclassMixin:

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__