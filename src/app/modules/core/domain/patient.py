from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any


@dataclass(slots=True)
class PatientAdditionalInfo:
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
class Patient:
    id: int
    full_name: str
    additional_info: PatientAdditionalInfo | None = None

    def set_anamnesis(self, anamnesis: str) -> None:
        if self.additional_info is None:
            raise ValueError("Patient has no additional info")

        self.additional_info.anamnesis = anamnesis

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'Patient':
        if data.get('additional_info'):
            additional_info_dict = data['additional_info']
            additional_info = PatientAdditionalInfo.from_mapping(additional_info_dict)
        else:
            additional_info = None
        data_dict = {
            'additional_info': additional_info,
            **data
        }

        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data_dict.items() if k in allowed}

        return Patient(**filtered)