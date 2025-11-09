from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import pandas as pd


@dataclass
class TimeSeriesPayload:
    metadata: Dict[str, Any]
    frame: pd.DataFrame


@dataclass
class SourceResult:
    context_lines: List[str] = field(default_factory=list)
    feedback: List[Tuple[str, str]] = field(default_factory=list)
    timeseries: Dict[str, TimeSeriesPayload] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

