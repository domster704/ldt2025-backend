from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.domain.patient import Patient, PatientAdditionalInfo
from app.modules.core.usecases.ports.patients import PatientPort


class PatientRepository(PatientPort):

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, patient_id: int) -> Patient | None:
        stmt = text(
            """
            SELECT * FROM patients WHERE id = :patient_id
            """
        )
        res = await self._session.execute(stmt, {"patient_id": patient_id})
        patient_row = res.one_or_none()
        patient = None
        if patient_row is not None:
            patient = Patient(
                id=patient_row[0],
                fio=patient_row[1],
            )
        return patient

    async def get_additional_info(self, patient_id: int) -> PatientAdditionalInfo | None:
        stmt = text(
            """
            SELECT * FROM patient_info WHERE patient_id = :patient_id
            """
        )
        res = await self._session.execute(stmt, {"patient_id": patient_id})
        add_info_row = res.one_or_none()
        add_info = None
        if add_info_row is not None:
            add_info = PatientAdditionalInfo(
                diagnosis=add_info_row[2],
                blood_gas_ph=add_info_row[3],
                blood_gas_co2=add_info_row[4],
                blood_gas_glu=add_info_row[5],
                blood_gas_lac=add_info_row[6],
                blood_gas_be=add_info_row[7],
            )

        return add_info

    async def get_ctgs(self, patient_id: int) -> Sequence[int]:
        stmt = text(
            """
            SELECT id FROM ctg_history WHERE patient_id = :patient_id
            """
        )
        res = await self._session.execute(stmt, {"patient_id": patient_id})
        return res.scalars().all()

    async def get_all(self) -> Sequence[Patient]:
        stmt = text("SELECT * FROM patients")
        res = await self._session.execute(stmt)
        rows = res.fetchall()
        return [
            Patient(
                id=row[0],
                fio=row[1],
            )
            for row in rows
        ]