from pydantic import BaseModel


class CardiotocographyPointDTO(BaseModel):
    bpm: float
    uc: float
    timestamp: float
