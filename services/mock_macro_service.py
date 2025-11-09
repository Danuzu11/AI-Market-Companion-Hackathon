from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import pandas as pd

from config.data_sources import REGIONAL_MACRO_REGIONS
from core.models import SourceResult


SYNTHETIC_MACRO_DATA: Dict[str, List[Dict[str, object]]] = {
    "asia": [
        {
            "indicator": "China Manufacturing PMI",
            "current": 50.8,
            "previous": 50.1,
            "units": "index",
            "date": "2025-09-30",
            "signal": "Manufacturing momentum improves alongside stimulus rollout.",
        },
        {
            "indicator": "Japan Core CPI",
            "current": 2.4,
            "previous": 2.6,
            "units": "% y/y",
            "date": "2025-09-30",
            "signal": "Inflation eases, keeping BoJ normalization cautious.",
        },
    ],
    "australia": [
        {
            "indicator": "Australia Unemployment Rate",
            "current": 4.1,
            "previous": 4.0,
            "units": "%",
            "date": "2025-08-31",
            "signal": "Labor market softens amid commodity price volatility.",
        },
        {
            "indicator": "RBA Cash Rate Outlook",
            "current": 4.35,
            "previous": 4.35,
            "units": "%",
            "date": "2025-09-16",
            "signal": "Policy on hold; board signals bias toward final hike if inflation re-accelerates.",
        },
    ],
    "europe": [
        {
            "indicator": "Eurozone Composite PMI",
            "current": 48.7,
            "previous": 49.1,
            "units": "index",
            "date": "2025-09-30",
            "signal": "Contraction deepens, particularly in Germany's manufacturing.",
        },
        {
            "indicator": "UK GDP q/q",
            "current": 0.3,
            "previous": 0.1,
            "units": "%",
            "date": "2025-09-30",
            "signal": "Services resilience offsets weak construction activity.",
        },
    ],
}


def fetch_regional_macro(regions: Optional[Iterable[str]] = None) -> SourceResult:
    selected = list(regions) if regions else list(SYNTHETIC_MACRO_DATA.keys())
    result = SourceResult()
    tables: Dict[str, pd.DataFrame] = {}

    for region_id in selected:
        entries = SYNTHETIC_MACRO_DATA.get(region_id)
        if not entries:
            continue

        label = REGIONAL_MACRO_REGIONS.get(region_id, region_id.title())
        df = pd.DataFrame(entries)
        tables[region_id] = df

        for row in entries:
            diff = None
            if row.get("previous") is not None and row.get("current") is not None:
                diff = row["current"] - row["previous"]
            diff_text = ""
            if diff is not None:
                diff_text = f" (Δ {diff:+.2f} {row['units']})"

            result.context_lines.append(
                f"{label}: {row['indicator']} {row['current']} {row['units']}{diff_text}. {row['signal']}"
            )

    if tables:
        result.extra["macro_tables"] = tables

    if not result.context_lines:
        result.feedback.append(
            (
                "info",
                "No se encontraron datos macroeconómicos ficticios para las regiones seleccionadas.",
            )
        )

    return result

