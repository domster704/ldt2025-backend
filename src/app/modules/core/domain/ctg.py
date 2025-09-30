from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.common.dataclass_mixins import DecimalPlaces, DecimalRoundingMixin


@dataclass(frozen=True, slots=True)
class CardiotocographyPoint(DecimalRoundingMixin):
    """ Точка КТГ """
    bmp: float
    uc:float
    timestamp: float