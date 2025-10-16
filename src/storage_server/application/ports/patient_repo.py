from typing import Protocol

from ...domain.patient import Patient


class PatientRepository(Protocol):

    async def save(self, patient: Patient) -> None: ...

    async def is_exists(self, patient_id: int) -> bool: ...

    async def read(self, patient_id: int) -> Patient | None: ...
