import os
import pickle
from pathlib import Path

from app.modules.ml.application.handlers.fetal_monitoring_handler import FetalMonitoringHandler
from app.modules.ml.infrastucture.services.fetal_monitoring import FetalMonitoringService

BASE_DIR = Path(__file__).resolve().parent
MODEL_CONFIG_PATH = BASE_DIR / "services" / "model_config.pkl"


def get_fetal_monitoring_handler() -> FetalMonitoringHandler:
    model_config = pickle.load(open(MODEL_CONFIG_PATH, 'rb'))
    processor = FetalMonitoringService(model_config)
    handler = FetalMonitoringHandler(fetal_monitoring_service=processor)
    return handler
