from sqlalchemy import Table, Column, Integer, String, ForeignKey, Float

from ..tables.base import metadata

patients = Table(
    "patients", metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", String, nullable=False),
)

patient_info = Table(
    "patient_info", metadata,
    Column("id", Integer, primary_key=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), nullable=False),
    Column("diagnosis", String),
    Column("blood_gas_ph", Float),
    Column("blood_gas_co2", Float),
    Column("blood_gas_glu", Float),
    Column("blood_gas_lac", Float),
    Column("blood_gas_be", Float),
    Column("anamnesis", String),
)