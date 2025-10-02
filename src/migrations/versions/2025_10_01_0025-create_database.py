"""create database

Revision ID: 7ec1afc86853
Revises: 
Create Date: 2025-10-01 00:25:01.740663+03:00

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import UniqueConstraint

# revision identifiers, used by Alembic.
revision: str = '7ec1afc86853'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'patients',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False, primary_key=True,
            comment='Идентификатор пациента'
        ),
        sa.Column(
            'full_name', sa.String(length=255), nullable=False,
            comment='ФИО пациента'
        ),
        comment='Пациенты'
    )

    op.create_table(
        'patient_info',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False, primary_key=True,
            comment='Идентификатор'
        ),
        sa.Column(
            'patient_id', sa.Integer(),
            sa.ForeignKey('patients.id', ondelete='CASCADE'),
            nullable=False,
            comment='Идентификатор пациента'
        ),
        sa.Column(
            'diagnosis', sa.Text(), nullable=True,
            comment='Диагноз пациента'
        ),
        sa.Column(
            'blood_gas_ph', sa.Float(), nullable=True,
            comment='Показатель кислотно-основного состояния крови'
        ),
        sa.Column(
            'blood_gas_co2', sa.Float(), nullable=True,
            comment='Парциальное давление углекислого газа'
        ),
        sa.Column(
            'blood_gas_glu', sa.Float(), nullable=True,
            comment='Уровень глюкозы в крови'
        ),
        sa.Column(
            'blood_gas_lac', sa.Float(), nullable=True,
            comment='Концентрация молочной кислоты (лактат)'
        ),
        sa.Column(
            'blood_gas_be', sa.Float(), nullable=True,
            comment='Базовый избыток, показатель кислотно-щелочного баланса'
        ),
        UniqueConstraint('id', 'patient_id'),
        comment='Информация о пациенте',
    )

    op.create_table(
        'ctg_history',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False, primary_key=True,
            comment='Идентификатор',
        ),
        sa.Column(
            'patient_id', sa.Integer(),
            sa.ForeignKey('patients.id', ondelete='CASCADE'),
            nullable=False,
            comment='Идентификатор пациента'
        ),
        sa.Column(
            'dir_path', sa.String(length=255), nullable=False,
            comment='Путь к директории с показателями КТГ'
        ),
        sa.Column(
            'archive_path', sa.String(length=255), nullable=True,
            comment='Путь к архиву, где находится КТГ'
        ),
        UniqueConstraint('id', 'patient_id'),
        comment='История проведения КТГ'
    )

    op.create_table(
        'ctg_results',
        sa.Column(
            'id', sa.Integer(), autoincrement=True, nullable=False, primary_key=True,
            comment='Идентификатор',
        ),
        sa.Column(
            'ctg_id', sa.Integer(),
            sa.ForeignKey('ctg_history.id', ondelete='CASCADE'),
            nullable=False,
            comment='Идентификатор КТГ'
        ),
        sa.Column(
            'gest_age', sa.String(length=255), nullable=False,
            comment='Срок беременности'
        ),
        sa.Column(
            'bpm', sa.Float(), nullable=False,
            comment='Частота сердечных сокращений'
        ),
        sa.Column(
            'uc', sa.Float(), nullable=False,
            comment='Маточные скоращения'
        ),
        sa.Column(
            'figo', sa.String(length=20), nullable=False,
            comment='Шкала оценки состояния плода/КТГ'
        ),
        sa.Column(
            'figo_prognosis', sa.String(length=20), nullable=False,
            comment='Прогноз FIGO'
        ),
        sa.Column(
            'bhr', sa.Float(), nullable=True, default=0,
            comment='Базальная ЧСС'
        ),
        sa.Column(
            'amplitude_oscillations', sa.Float(), nullable=True, default=0,
            comment='Амплитуда осцилляций'
        ),
        sa.Column(
            'oscillation_frequency', sa.Float(), nullable=True, default=0,
            comment='Частота осцилляций'
        ),
        sa.Column(
            'ltv', sa.Integer(), nullable=True, default=0,
            comment='ДББ за сеанс'
        ),
        sa.Column(
            'stv', sa.Integer(), nullable=True, default=0,
            comment='КВВ за сеанс'
        ),
        sa.Column(
            'stv_little', sa.Integer(), nullable=True, default=0,
            comment='КВВ за 10 минут'
        ),
        sa.Column(
            'accellations', sa.Integer(), nullable=True, default=0,
            comment='Акцелерации >15 уд/мин'
        ),
        sa.Column(
            'deceleration', sa.Integer(), nullable=True, default=0,
            comment='Децелерации все'
        ),
        sa.Column(
            'uterine_contractions', sa.Integer(), nullable=True, default=0,
            comment='Кол-во сокращений матки'
        ),
        sa.Column(
            'fetal_movements', sa.Integer(), nullable=True, default=0,
            comment='Шевелений плода, за сеанс'
        ),
        sa.Column(
            'fetal_movements_little', sa.Integer(), nullable=True, default=0,
            comment='Шевелений плода, в час'
        ),
        sa.Column(
            'accellations_little', sa.Integer(), nullable=True, default=0,
            comment='Акцелерации >10 уд/мин'
        ),
        sa.Column(
            'deceleration_little', sa.Integer(), nullable=True, default=0,
            comment='Децелерации S>20 ударов'
        ),
        sa.Column(
            'high_variability', sa.Integer(), nullable=True, default=0,
            comment='Высокая вариабельность, мин'
        ),
        sa.Column(
            'low_variability', sa.Integer(), nullable=True, default=0,
            comment='Низкая вариабельность, мин'
        ),
        sa.Column(
            'loss_signals', sa.Float(), nullable=True, default=0,
            comment='Потеря сигнала (%)'
        ),
        sa.Column(
            'created_at', sa.Date(), nullable=False, default=datetime.now(),
            comment='Дата обследования'
        ),
        UniqueConstraint('id', 'ctg_id'),
        comment='Результаты КТГ'
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ctg_results')
    op.drop_table('ctg_history')
    op.drop_table('patient_info')
    op.drop_table('patients')