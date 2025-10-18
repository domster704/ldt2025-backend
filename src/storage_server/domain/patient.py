from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any

from pydantic import BaseModel

from .mixin import DataclassMixin
from ..infrastructure.tables.patients import patient_info_table


@dataclass(frozen=True, slots=True)
class PatientAdditionalInfo(DataclassMixin):
    diagnosis: str | None
    blood_gas_ph: float | None
    blood_gas_co2: float | None
    blood_gas_glu: float | None
    blood_gas_lac: float | None
    blood_gas_be: float | None
    anamnesis: str | None

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'PatientAdditionalInfo':
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}

        return PatientAdditionalInfo(**filtered)

@dataclass(frozen=True, slots=True)
class Patient(DataclassMixin):
    id: int | None
    full_name: str
    additional_info: PatientAdditionalInfo | None = None

    def has_additional_info(self) -> bool:
        return self.additional_info is not None

    @classmethod
    def from_db(cls, data: Mapping[str, Any]) -> 'Patient':
        patient_add_info = PatientAdditionalInfo.from_db(data)
        data_dict = {
            'additional_info': patient_add_info,
            **data
        }

        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data_dict.items() if k in allowed}

        return Patient(**filtered)

    @staticmethod
    def from_dto(dto: BaseModel) -> 'Patient':
        data = dto.model_dump()

        add = data.get("additional_info")
        add_obj: PatientAdditionalInfo | None
        if add is None:
            add_obj = None
        elif isinstance(add, BaseModel):
            add_obj = PatientAdditionalInfo(**add.model_dump())
        elif isinstance(add, Mapping):
            add_obj = PatientAdditionalInfo(**add)
        else:
            add_obj = PatientAdditionalInfo(**dict(add))

        return Patient(
            id=data.get("id"),
            full_name=data["full_name"],
            additional_info=add_obj,
        )
