from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PatientAdditionalInfo:
    diagnosis: str | None
    blood_gas_ph: float | None
    blood_gas_co2: float | None
    blood_gas_glu: float | None
    blood_gas_lac: float | None
    blood_gas_be: float | None
    anamnesis: str | None

@dataclass(slots=True)
class Patient:
    id: int
    fio: str
    additional_info: PatientAdditionalInfo | None = None
