from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.modules.core.domain.patient import Patient


@dataclass(frozen=True, slots=True)
class PatientAdditionalInfo:
    diagnosis: str | None
    blood_gas_ph: float | None
    blood_gas_co2: float | None
    blood_gas_glu: float | None
    blood_gas_lac: float | None
    blood_gas_be: float | None
    anamnesis: str | None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__

@dataclass(frozen=True, slots=True)
class Patient:
    id: int | None
    full_name: str
    additional_info: PatientAdditionalInfo | None = None

    def from_db_row(self, row: Mapping[str, Any]) -> Patient:
        return Patient(**row)

    def has_additional_info(self) -> bool:
        return self.additional_info is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "additional_info": self.additional_info.to_dict(),
        }