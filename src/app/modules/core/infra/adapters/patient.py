from app.modules.core.domain.patient import Patient
from app.modules.core.infra.adapters.db_mixin import DBMixin
from app.modules.core.usecases.ports.patients import PatientPort


class PatientRepository(PatientPort, DBMixin):

    async def get_by_id(self, patient_id: int) -> Patient | None:
        session = self.get_session()
        res = await session.execute()
