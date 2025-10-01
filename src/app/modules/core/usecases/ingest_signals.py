from app.modules.core.domain.ctg_point import CardiotocographyPoint
from ..usecases.ports.signals import SignalsPort


async def ingest_signals_and_save(
        signal: CardiotocographyPoint,
        signal_port: SignalsPort
):
    """ Получение сигналов и их сохранение """
    signal_port.save(signal)
