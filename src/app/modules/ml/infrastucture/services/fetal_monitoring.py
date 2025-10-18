from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from app.modules.ml.application.interfaces.fetal_monitoring import IFetalMonitoring
from app.modules.ml.domain.entities.process import Process, ProcessResults, TimeRange
from app.modules.ml.infrastucture.services.context import StreamContext
from app.modules.ml.infrastucture.services.stages import (
    AdvancedAccelDecelStage,
    ContractionStage,
    FigoStage,
    FisherClassicStage,
    IngestionStage,
    ModelsStage,
    SavelyevaScoreStage,
    Stage,
    StatusComposerStage,
    STV10MinStage,
    TachyBradyStage,
)
from app.modules.ml.infrastucture.services.utils import (
    calculate_stv,
    median_last_seconds,
    rolling_stv_mean_10min,
)


@dataclass
class STVModelsConfig:
    window_size: int
    step_size: int
    models: Dict[str, Dict[str, Any]]


@dataclass
class HypoxiaModelConfig:
    model: Any
    fs: int = 5
    ewma_alpha: float = 0.01


class StreamingPipeline:
    """Соединяет стадии вместе; один .step(df) = одна секунда обработки."""

    def __init__(self, ctx: StreamContext, stages: List[Stage]):
        self.ctx = ctx
        self.stages = stages

    def step(self, df: pd.DataFrame) -> Process:
        # update source df (new rows may have arrived)
        self.ctx.current_df = df if df is not None else self.ctx.current_df

        # run stages in order
        for stage in self.stages:
            stage.tick(self.ctx)

        # snapshot -> Process
        ln = self.ctx.nc.last_notification
        return Process(
            time_sec=self.ctx.now_t,
            current_status=ln.get("current_status"),
            notifications=self.ctx.nc.notifications,
            figo_situation=ln.get("figo_situation"),
            savelyeva_score=ln.get("savelyeva_score"),
            savelyeva_category=ln.get("savelyeva_category"),
            fischer_score=ln.get("fischer_score"),
            fischer_category=ln.get("fischer_category"),
            current_fhr=ln.get("current_fhr"),
            current_uterus=ln.get("current_uterus"),
            stv=ln.get("stv"),
            stv_forecast=ln.get("stv_forecast"),
            accelerations_count=ln.get("accelerations_count"),
            decelerations_count=ln.get("decelerations_count"),
            median_fhr_10min=ln.get("median_fhr_10min"),
            hypoxia_proba=ln.get("hypoxia_proba"),
        )


def finalize_results(ctx: StreamContext) -> ProcessResults:
    df = ctx.current_df
    if df is None or df.empty:
        return ProcessResults(
            last_figo=None,
            baseline_bpm=None,
            stv_all=None,
            stv_10min_mean=None,
            accelerations_count=0,
            decelerations_count=0,
            uterus_mean=None,
        )
    last_figo = ctx.nc.last_notification.get("figo_situation")
    last_savelyeva = ctx.nc.last_notification.get("savelyeva_score")
    last_savelyeva_category = ctx.nc.last_notification.get("savelyeva_category")
    last_fischer = ctx.nc.last_notification.get("fischer_score")
    last_fischer_category = ctx.nc.last_notification.get("fischer_category")

    baseline_bpm = median_last_seconds(ctx.sec_fhr, ctx.now_t, 1200)
    if baseline_bpm is not None:
        baseline_bpm = float(round(baseline_bpm, 1))

    fhr_all = df["value_bpm"].astype(float).values
    stv_all = calculate_stv(fhr_all, fs=ctx.fs)
    stv_all = None if np.isnan(stv_all) else float(round(stv_all, 2))

    stv_10min_mean = rolling_stv_mean_10min(fhr_all, fs=ctx.fs)
    stv_10min_mean = (
        None if np.isnan(stv_10min_mean) else float(round(stv_10min_mean, 2))
    )

    accelerations_count = sum(
        1 for a in ctx.nc.last_notification["accelerations"] if a["start"] is not None
    )
    decelerations_count = sum(
        1 for d in ctx.nc.last_notification["decelerations"] if d["start"] is not None
    )

    uterus_mean = (
        float(df["value_uterus"].astype(float).mean())
        if not df["value_uterus"].empty
        else None
    )
    if uterus_mean is not None and not pd.isna(uterus_mean):
        uterus_mean = float(round(uterus_mean, 2))
    else:
        uterus_mean = None

    return ProcessResults(
        last_figo=last_figo,
        last_savelyeva=last_savelyeva,
        last_savelyeva_category=last_savelyeva_category,
        last_fischer=last_fischer,
        last_fischer_category=last_fischer_category,
        baseline_bpm=baseline_bpm,
        stv_all=stv_all,
        stv_10min_mean=stv_10min_mean,
        accelerations_count=int(accelerations_count),
        decelerations_count=int(decelerations_count),
        uterus_mean=uterus_mean,
    )


class FetalMonitoringService(IFetalMonitoring):

    def __init__(
        self, model_hypoxia_config: Dict[str, Any], model_stv_config: Dict[str, Any]
    ):
        fs = model_hypoxia_config.get("fs", 5)
        self.ctx = StreamContext(
            fs=fs,
            stv_cfg=model_stv_config,
            hypoxia_cfg=HypoxiaModelConfig(
                model=model_hypoxia_config["model"],
                fs=fs,
                ewma_alpha=model_hypoxia_config.get("ewma_alpha", 0.01),
            ),
        )
        self.pipeline = StreamingPipeline(
            self.ctx,
            stages=[
                IngestionStage(),
                ContractionStage(),
                TachyBradyStage(),
                STV10MinStage(),
                AdvancedAccelDecelStage(),
                ModelsStage(),
                FigoStage(),
                SavelyevaScoreStage(),
                StatusComposerStage(),
                FisherClassicStage(),
            ],
        )

    def process_stream(self, df: pd.DataFrame) -> Process:
        return self.pipeline.step(df)

    def finalize_process(self) -> ProcessResults:
        return finalize_results(self.ctx)

    # === Optional: keep your static analyzer for day-level dynamics ===
    @staticmethod
    def analyze_patient_dynamics(df: pd.DataFrame) -> str:
        notes = []
        last_baseline = df["baseline_bpm"].iloc[-1]
        if last_baseline > 160:
            notes.append("Повышенная базальная ЧСС (тахикардия)")
        elif last_baseline < 110:
            notes.append("Пониженная базальная ЧСС (брадикардия)")
        else:
            notes.append("Базальная ЧСС в норме")

        last_stv = df["stv_all"].iloc[-1]
        if last_stv < 3:
            notes.append("Низкая STV, возможный риск гипоксии")
        elif last_stv > 6:
            notes.append("Высокая вариабельность")
        else:
            notes.append("STV в пределах нормы")

        acc = df["accelerations_count"].iloc[-1]
        notes.append(
            f"Наблюдаются акцелерации ({acc} за день)"
            if acc >= 3
            else "Акцелерации незначительные"
        )

        X = np.arange(len(df)).reshape(-1, 1)
        y = df["baseline_bpm"].values
        slope = LinearRegression().fit(X, y).coef_[0]
        if slope > 0.6:
            notes.append(
                f"Тренд на повышение базальной ЧСС (+{slope:.2f} уд/мин в день)"
            )
        elif slope > 0.1:
            notes.append(
                f"Небольшой тренд на повышение базальной ЧСС (+{slope:.2f} уд/мин в день)"
            )
        elif slope < -0.6:
            notes.append(f"Тренд на снижение базальной ЧСС ({slope:.2f} уд/мин в день)")
        elif slope < -0.1:
            notes.append(
                f"Небольшой тренд на снижение базальной ЧСС ({slope:.2f} уд/мин в день)"
            )
        else:
            notes.append("Тренд базальной ЧСС стабильный")

        return " | ".join(notes)
