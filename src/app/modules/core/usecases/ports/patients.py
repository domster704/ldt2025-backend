from typing import Protocol

from app.modules.core.domain.patient import Patient, PatientAdditionalInfo


class PatientPort(Protocol):

    async def get_by_id(self, patient_id: int) -> Patient | None: ...

    async def list(self, patient_ids: list[int] | None = None) -> list[Patient]: ...

    async def get_additional_info(self, patient_id: int) -> PatientAdditionalInfo | None: ...

    async def get_ctgs(self, patient_id: int) -> list[int]: ...