from typing import Sequence, override

from sqlalchemy import text, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.domain.patient import Patient, PatientAdditionalInfo
from app.modules.core.infra.tables.patients import patients_table, patient_info_table
from app.modules.core.usecases.ports.patient_repository import PatientRepository


class SQLAlchemyPatientRepository(PatientRepository):

    def __init__(self, session: AsyncSession):
        self._session = session

    @override
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
                full_name=patient_row[1],
            )
        return patient

    @override
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
                diagnosis=add_info_row[1],
                blood_gas_ph=add_info_row[2],
                blood_gas_co2=add_info_row[3],
                blood_gas_glu=add_info_row[4],
                blood_gas_lac=add_info_row[5],
                blood_gas_be=add_info_row[6],
                anamnesis=add_info_row[7],
            )

        return add_info

    @override
    async def get_ctgs(self, patient_id: int) -> Sequence[int]:
        stmt = text(
            """
            SELECT id FROM ctg_history WHERE patient_id = :patient_id
            """
        )
        res = await self._session.execute(stmt, {"patient_id": patient_id})
        return res.scalars().all()

    @override
    async def get_all(self) -> Sequence[Patient]:
        stmt = text("SELECT * FROM patients")
        res = await self._session.execute(stmt)
        rows = res.fetchall()
        return [
            Patient(
                id=row[0],
                full_name=row[1],
            )
            for row in rows
        ]

    @override
    async def save(self, patient: Patient) -> None:
        patient_dict = patient.to_dict()
        add_info_dict: None | dict = None
        if patient.has_additional_info():
            add_info_dict = patient_dict.pop("additional_info")
        patient_stmt = (
            insert(patients_table)
            .values(**patient_dict)
            .returning(patients_table.c.id)
        )
        patient_id = (await self._session.execute(patient_stmt)).scalar_one()
        if add_info_dict:
            add_info_dict['patient_id'] = patient_id
            add_info_stmt = (
                insert(patient_info_table)
                .values(**add_info_dict)
            )
            await self._session.execute(add_info_stmt)
        await self._session.commit()

    @override
    async def patient_exists(self, patient_id: int) -> bool:
        stmt = text("SELECT * FROM patients WHERE id = :patient_id")
        resp = await self._session.execute(stmt, {"patient_id": patient_id})
        db_object = resp.one_or_none()
        if db_object is None:
            return False
        return True