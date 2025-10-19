from typing import Any, override, Self

from pydantic import BaseModel

from ..usecases.ports.llm_message_builder import AnamnesisMessageBuilderProtocol


class MessageAttributes(BaseModel):
    diagnosis: str | None = None
    blood_gas_ph: str | None = None
    blood_gas_co2: str | None = None
    blood_gas_glu: str | None = None
    blood_gas_lac: str | None = None
    blood_gas_be: str | None = None


class AnamnesisMessageBuilder(AnamnesisMessageBuilderProtocol):
    def __init__(self):
        self._attributes = MessageAttributes()

    @override
    def add_diagnosis(self, diagnosis: str | None) -> Self:
        clean_diagnosis = diagnosis.replace('\n', ' ').strip()
        self._attributes.diagnosis = clean_diagnosis
        return self

    @override
    def add_blood_gas_ph(self, blood_gas_ph: float | None) -> Self:
        self._attributes.blood_gas_ph = str(blood_gas_ph).replace('.', ',')
        return self

    @override
    def add_blood_gas_co2(self, blood_gas_co2: float | None) -> Self:
        self._attributes.blood_gas_co2 = str(blood_gas_co2).replace('.', ',')
        return self

    @override
    def add_blood_gas_glu(self, blood_gas_glu: float | None) -> Self:
        self._attributes.blood_gas_glu = str(blood_gas_glu).replace('.', ',')
        return self

    @override
    def add_blood_gas_lac(self, blood_gas_lac: float | None) -> Self:
        self._attributes.blood_gas_lac = str(blood_gas_lac).replace('.', ',')
        return self

    @override
    def add_blood_gas_be(self, blood_gas_be: float | None) -> Self:
        self._attributes.blood_gas_be = str(blood_gas_be).replace('.', ',')
        return self

    def _replace_none(self, value: Any) -> Any:
        if value is None:
            return 'неизвестно'

    @override
    def build(self) -> str:
        message = (
            'Информация о беременной женщине. '
            f'Диагноз: {self._replace_none(self._attributes.diagnosis)}. '
            f'Кислотно-щелочной показатель газов крови (pH): {self._replace_none(self._attributes.blood_gas_ph)}. '
            f'Парциальное давление CO₂ в газах крови (pCO₂): {self._replace_none(self._attributes.blood_gas_ph)}. '
            f'Глюкоза в газах крови: {self._replace_none(self._attributes.blood_gas_ph)}. '
            f'Лактат в газах крови: {self._replace_none(self._attributes.blood_gas_ph)}. '
            f'База/избыток оснований (Base Excess) в газах крови: {self._replace_none(self._attributes.blood_gas_ph)}. '
            f'Предоставь анамез.'
        )
        return message