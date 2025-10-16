from sqlalchemy import Table, Column, Integer, ForeignKey, String

from .base import metadata

ctg_history_table = Table(
    'ctg_history', metadata,
    Column('id', Integer, primary_key=True),
    Column('patient_id', Integer, ForeignKey('patients.id')),
    Column('file_path_in_archive', String, nullable=False),
    Column('archive_path', String, nullable=False),
)