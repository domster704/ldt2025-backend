import os
import pickle
from pathlib import Path

from app.modules.ml.application.handlers.fetal_monitoring_handler import (
    FetalMonitoringHandler,
)
from app.modules.ml.infrastucture.services.fetal_monitoring import (
    FetalMonitoringService,
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_HYPOXIA_CONFIG_PATH = BASE_DIR / "services" / "model_hypoxia_config.pkl"
MODEL_STV_CONFIG_PATH = BASE_DIR / "services" / "model_stv_config.pkl"


def get_fetal_monitoring_handler() -> FetalMonitoringHandler:
    model_hypoxia_config = pickle.load(open(MODEL_HYPOXIA_CONFIG_PATH, "rb"))
    model_stv_config = pickle.load(open(MODEL_STV_CONFIG_PATH, "rb"))
    processor = FetalMonitoringService(model_hypoxia_config, model_stv_config)
    handler = FetalMonitoringHandler(fetal_monitoring_service=processor)
    return handler
