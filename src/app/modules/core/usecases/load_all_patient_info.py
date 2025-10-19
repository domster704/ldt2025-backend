from .ports.llm_gateway import LLMGateway
from .ports.llm_message_builder import AnamnesisMessageBuilderProtocol
from .ports.patient_gateway import PatientGateway
from ..infra.repositories.ctg import SQLAlchemyCTGRepository
from ..infra.repositories.patient import SQLAlchemyPatientRepository


async def load_all_patient_info(
        patient_id: int,
        patient_gtw: PatientGateway,
        patient_repo: SQLAlchemyPatientRepository,
        llm_gtw: LLMGateway,
        anamnesis_builder: AnamnesisMessageBuilderProtocol,
        ctg_repo: SQLAlchemyCTGRepository
) -> None:
        patient = await patient_gtw.load_patient(patient_id)
        query = (
                anamnesis_builder
                .add_diagnosis(patient.additional_info.diagnosis)
                .add_blood_gas_ph(patient.additional_info.blood_gas_ph)
                .add_blood_gas_co2(patient.additional_info.blood_gas_co2)
                .add_blood_gas_glu(patient.additional_info.blood_gas_glu)
                .add_blood_gas_lac(patient.additional_info.blood_gas_lac)
                .add_blood_gas_be(patient.additional_info.blood_gas_be)
                .build()
        )
        anamnesis = await llm_gtw.get_anamnesis(query)
        patient.set_anamnesis(anamnesis)
        await patient_repo.save(patient)
        ctg_history = await patient_gtw.load_patient_ctg_history(patient_id)
        ctg_ids = await ctg_repo.add_histories(ctg_history, patient_id)
        await patient_gtw.load_patient_ctg_results(ctg_ids)
