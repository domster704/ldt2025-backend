from sqlalchemy import Table, Column, Integer, Float, String, ForeignKey

from ..tables.base import metadata

ctg_results_table = Table(
    'ctg_results', metadata,
    Column('ctg_id', Integer, ForeignKey('ctg_history.id'), primary_key=True),
    Column('gest_age', String(255)),
    Column('bpm', Float),
    Column('uc', Float),
    Column('figo', String(20)),
    Column('figo_prognosis', String(20)),
    Column('bhr', Float),
    Column('amplitude_oscillations', Float),
    Column('oscillation_frequency', Float),
    Column('ltv', Integer),
    Column('stv', Integer),
    Column('stv_little', Integer),
    Column('accelerations', Integer),
    Column('decelerations', Integer),
    Column('uterine_contractions', Integer),
    Column('fetal_movements', Integer),
    Column('fetal_movements_little', Integer),
    Column('accelerations_little', Integer),
    Column('deceleration_little', Integer),
    Column('high_variability', Integer),
    Column('low_variability', Integer),
    Column('loss_signals', Float),
)