from pydantic import BaseModel


class CTGResultReadOutDTO(BaseModel):
    gest_age: str | None
    bpm: float | None
    uc: float | None
    figo: str | None
    figo_prognosis: str | None
    bhr: float | None
    amplitude_oscillations: float | None
    oscillation_frequency: float | None
    ltv: int | None
    stv: int | None
    stv_little: int | None
    accelerations: int | None
    decelerations: int | None
    uterine_contractions: int | None
    fetal_movements: int | None
    fetal_movements_little: int | None
    accelerations_little: int | None
    deceleration_little: int | None
    high_variability: int | None
    low_variability: int | None
    loss_signals: float | None
    fischer_status: str | None
    savelyeva_status: str | None

class CTGResultAddInDTO(BaseModel):
    ctg_id: int
    gest_age: str
    bpm: float
    uc: float
    figo: str
    figo_prognosis: str
    bhr: float
    amplitude_oscillations: float
    oscillation_frequency: float
    ltv: int
    stv: int
    stv_little: int
    accelerations: int
    decelerations: int
    uterine_contractions: int
    fetal_movements: int
    fetal_movements_little: int
    accelerations_little: int
    deceleration_little: int
    high_variability: int
    low_variability: int
    loss_signals: float
    fischer_status: str
    savelyeva_status: str
