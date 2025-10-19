from collections.abc import Sequence
from typing import Protocol

from app.modules.core.domain.patient import Patient, PatientAdditionalInfo


class PatientRepository(Protocol):

    async def get_by_id(self, patient_id: int) -> Patient | None: ...

    async def get_additional_info(self, patient_id: int) -> PatientAdditionalInfo | None: ...

    async def get_ctgs(self, patient_id: int) -> Sequence[int]: ...

    async def get_all(self) -> Sequence[Patient]: ...

    async def save(self, patient: Patient) -> None: ...
