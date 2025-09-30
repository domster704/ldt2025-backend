from dataclasses import dataclass, field
from decimal import Decimal

from mypyc.namegen import Iterable

from app.common.dataclass_mixins import DecimalPlaces, DecimalRoundingMixin


@dataclass(frozen=True, slots=True)
class PredictMetrics(DecimalRoundingMixin):
    slope_bpm_min: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    sdnn: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    rmssd: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    pnn5: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    baseline_med: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    vmin: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    vmax: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    missing_ratio: Decimal = field(metadata={'precision': DecimalPlaces.TWO})
    est_fs: Decimal = field(metadata={'precision': DecimalPlaces.TWO})

@dataclass(frozen=True, slots=True)
class CTGPredict:
    metrics: PredictMetrics
    alerts: Iterable[str] | None