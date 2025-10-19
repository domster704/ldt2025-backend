from pydantic import BaseModel

from .ctg_result import CTGResultReadOutDTO


class CTGHistoryReadOutDTO(BaseModel):
    id: int
    file_path_in_archive: str
    ctg_result: CTGResultReadOutDTO | None = None

class CTGHistoryAddInDTO(BaseModel):
    patient_id: int
    file_path_in_archive: str
    archive_path: str