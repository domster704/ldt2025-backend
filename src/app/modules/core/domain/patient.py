from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any

from app.modules.core.domain.mixin import ToDictMixin


@dataclass(slots=True)
class PatientAdditionalInfo(ToDictMixin):
    diagnosis: str | None
    blood_gas_ph: float | None
    blood_gas_co2: float | None
    blood_gas_glu: float | None
    blood_gas_lac: float | None
    blood_gas_be: float | None
    anamnesis: str | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> 'PatientAdditionalInfo':
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}

        return PatientAdditionalInfo(**filtered)

@dataclass(slots=True)
class Patient(ToDictMixin):
    id: int
    full_name: str
    additional_info: PatientAdditionalInfo | None = None

    def set_anamnesis(self, anamnesis: str) -> None:
        if self.additional_info is None:
            raise ValueError("Patient has no additional info")

        self.additional_info.anamnesis = anamnesis

    def has_anamnesis(self) -> bool:
        if self.additional_info is None:
            return False

        return self.additional_info.anamnesis is not None

    def has_additional_info(self) -> bool:
        return self.additional_info is not None

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'Patient':
        data_dict = dict(**data)
        if not data.get('additional_info'):
            data_dict['additional_info'] = None

        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data_dict.items() if k in allowed}

        patient = Patient(**filtered)
        if data_dict['additional_info']:
            patient_additional_info = PatientAdditionalInfo.from_mapping(data_dict['additional_info'])
            patient.additional_info = patient_additional_info
        return patient
