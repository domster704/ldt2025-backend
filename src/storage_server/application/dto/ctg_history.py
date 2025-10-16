from pydantic import BaseModel


class CTGHistoryReadOutDTO(BaseModel):
    id: int
    file_path_in_archive: str
    archive_path: str

class CTGHistoryAddInDTO(BaseModel):
    patient_id: int
    file_path_in_archive: str
    archive_path: str