import tempfile
from pathlib import Path
from typing import override

from httpx import AsyncClient

from ...domain.ctg import CTGHistory
from ...domain.patient import Patient
from ...usecases.ports.patient_gateway import PatientGateway


class HttpxPatientGateway(PatientGateway):
    def __init__(self, client: AsyncClient):
        self._client = client

    @override
    async def load_patient(self, patient_id: int) -> Patient:
        try:
            resp = await self._client.get(f'/patients/{patient_id}')
        except Exception as e:
            raise
        resp.raise_for_status()
        return Patient.from_db(resp.json())

    @override
    async def load_patient_ctg_history(self, patient_id: int) -> list[CTGHistory]:
        try:
            resp = await self._client.get(f'/ctg_history/{patient_id}')
        except Exception as e:
            raise
        resp.raise_for_status()
        return [CTGHistory.from_mapping(ctg_history) for ctg_history in resp.json()]

    @override
    async def load_patient_ctg_graphics(self, patient_id: int) -> Path:
        resp = await self._client.get(f'/ctg_graphics', params={'patient_id': patient_id})
        resp.raise_for_status()
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.write(resp.content)
        tmp_file.close()

        return Path(tmp_file.name)