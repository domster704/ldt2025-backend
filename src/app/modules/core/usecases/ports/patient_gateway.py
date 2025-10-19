from typing import Protocol

from ...domain.ctg import CTGHistory, CTGResult
from ...domain.patient import Patient

class UnexpectedError(Exception):
    pass

class PatientNotFound(Exception):
    pass

class PatientGateway(Protocol):
    async def load_patient(self, patient_id: int) -> Patient: ...

    async def load_patient_ctg_history(self, patient_id: int) -> list[CTGHistory]: ...

    async def load_patient_ctg_results(self, ctgs_id: list[int]) -> list[CTGResult]: ...

    async def load_patient_ctg_graphics(self, patient_id: int) -> ...: ...