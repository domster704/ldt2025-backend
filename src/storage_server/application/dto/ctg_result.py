from pydantic import BaseModel


class CTGResultReadOutDTO(BaseModel):
    id: int
    slope_bpm_min: float
    sdnn: float
    rmssd: float
    pnn5: float
    baseline_med: float
    vmin: float
    vmax: float
    missing_ratio: float
    est_fs: float

class CTGResultAddInDTO(BaseModel):
    ctg_id: int
    slope_bpm_min: float
    sdnn: float
    rmssd: float
    pnn5: float
    baseline_med: float
    vmin: float
    vmax: float
    missing_ratio: float
    est_fs: float
