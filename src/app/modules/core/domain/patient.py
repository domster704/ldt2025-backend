from dataclasses import dataclass


@dataclass(slots=True)
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

    def set_anamnesis(self, anamnesis: str) -> None:
        if self.additional_info is None:
            raise ValueError("Patient has no additional info")

        self.additional_info.anamnesis = anamnesis