from datetime import datetime

from pydantic import BaseModel


class CTGGraphicFileAddInDTO(BaseModel):
    patient_id: int
    ctg_datetime: datetime
    file: bytes

    @property
    def filename(self) -> str:
        return self.ctg_datetime.strftime("%Y%m%d%H%M%S") + '.csv'