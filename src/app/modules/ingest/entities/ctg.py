from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CardiotocographyPoint:
    """ Точка КТГ """
    bpm: float
    uc: float
    timestamp: float
