from pathlib import Path

from pydantic import BaseModel


class CTGGraphicFileAddInDTO(BaseModel):
    patient_id: int
    ctg_graphic_file_path: Path