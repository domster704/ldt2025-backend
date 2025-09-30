from typing import Protocol

import pandas as pd

from app.modules.ml.domain.entities.process import Process


class IFetalMonitoring(Protocol):
    def process_stream(
            self, df: pd.DataFrame
    ) -> Process:
        ...
