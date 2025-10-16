from pydantic import BaseModel


class PatientAddInfo(BaseModel):
    diagnosis: str | None
    blood_gas_ph: float | None
    blood_gas_co2: float | None
    blood_gas_glu: float | None
    blood_gas_lac: float | None
    blood_gas_be: float | None
    anamnesis: str | None

class PatientReadOutDTO(BaseModel):
    id: int | None
    full_name: str
    additional_info: PatientAddInfo | None = None

class PatientAddInDTO(BaseModel):
    full_name: str
    additional_info: PatientAddInfo | None = None

class PatientUpdateInDTO(BaseModel):
    id: int | None
    full_name: str
    additional_info: PatientAddInfo | None = None