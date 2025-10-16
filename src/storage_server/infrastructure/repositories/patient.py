from typing import override

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..tables.patients import patients, patient_info
from ...application.ports.patient_repo import PatientRepository
from ...domain.patient import Patient


class SQLAlchemyPatientRepository(PatientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def read(self, patient_id: int) -> Patient | None:
        stmt = text(
        """
            SELECT * FROM patients WHERE id = :patient_id
        """
        )
        result = await self._session.execute(stmt, {"patient_id": patient_id})

        if (patient_object := result.one_or_none()) is None:
            return None

        patient = Patient.from_db_row(patient_object._mapping)
        return patient

    @override
    async def save(self, patient: Patient) -> None:
        patient_base_dict = patient.to_dict()
        patient_id = patient_base_dict.pop("id")
        patient_base_dict.pop("additional_info")

        stmt_patient_base = (
            insert(patients)
            .values({"id": patient_id, **patient_base_dict})
            .on_conflict_do_update(
                index_elements=[patients.c.id],
                set_=patient_base_dict,
            )
            .returning(patients.c.id)
        )
        new_patient_id = (await self._session.execute(stmt_patient_base)).scalar_one()

        if patient.has_additional_info():
            patient_add_info_dict = patient.additional_info.to_dict()
            stmt_patient_add_info = (
                insert(patient_info)
                .values({"patient_id": new_patient_id, **patient_add_info_dict})
                .on_conflict_do_update(
                    index_elements=[patient_info.c.patient_id],
                    set_=patient_add_info_dict,
                )
            )
            await self._session.execute(stmt_patient_add_info, )

        await self._session.commit()