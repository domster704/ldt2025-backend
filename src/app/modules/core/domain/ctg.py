from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.common.dataclass_mixins import DecimalPlaces, DecimalRoundingMixin


@dataclass(frozen=True, slots=True)
class CardiotocographyPoint(DecimalRoundingMixin):
    """ Точка КТГ """
    bmp: Decimal | None = field(metadata={'precision': DecimalPlaces.TWO})
    uc: Decimal | None = field(metadata={'precision': DecimalPlaces.TWO})
    timestamp: datetime

@dataclass(frozen=True, slots=True)
class Cardiotocography:
    """ КГТ """
    points: Iterable[CardiotocographyPoint] = field(default_factory=list)
