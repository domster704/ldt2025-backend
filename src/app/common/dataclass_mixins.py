from dataclasses import fields
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

class DecimalPlaces(Enum):
    TWO = Decimal('0.01')

class DecimalRoundingMixin:
    """Миксин для реализации округления Decimal в датаклассах"""

    _ROUNDING: str = ROUND_HALF_UP

    @classmethod
    def _normalize_decimal(cls, value: Any, precision_digits: Decimal) -> Decimal | None:
        """Преобразует значение в Decimal и округляет до указанного формата"""
        if value is None:
            return None

        if isinstance(value, int | float):
            value = Decimal(value)

        if isinstance(value, Decimal):
            return value.quantize(precision_digits, cls._ROUNDING)

        raise TypeError(
            f'Ожидался int/float/Decimal или None, получено {type(value).__name__!s}'
        )

    def _normalize_decimals(self) -> None:
        for f in fields(self):
            precision_digits: Decimal | None = f.metadata.get('precision')
            if precision_digits is None:
                continue

            rounded = self._normalize_decimal(getattr(self, f.name), precision_digits)
            setattr(self, f.name, rounded)