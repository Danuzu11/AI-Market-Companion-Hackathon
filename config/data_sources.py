from typing import Dict, List

FRED_SERIES: Dict[str, Dict[str, str]] = {
    "PIB real (GDPC1)": {
        "series_id": "GDPC1",
        "value_format": "billions",
        "description": "Producto Interno Bruto real de Estados Unidos (precios encadenados de 2017).",
    },
    "Tasa de desempleo (UNRATE)": {
        "series_id": "UNRATE",
        "value_format": "percent",
        "description": "Tasa de desempleo civil en Estados Unidos.",
    },
    "Índice de precios al consumidor (CPIAUCSL)": {
        "series_id": "CPIAUCSL",
        "value_format": "index",
        "description": "Índice de precios al consumidor para todos los consumidores urbanos.",
    },
}

DEFAULT_FRED_SELECTION = list(FRED_SERIES.keys())[:2]
DEFAULT_FRED_RANGE_DAYS = 365 * 3

REGIONAL_MACRO_REGIONS: Dict[str, str] = {
    "asia": "Asia Pacific",
    "australia": "Australia & Oceania",
    "europe": "Europe",
}

NEWS_CATEGORIES: List[str] = [
    "Macro Policy",
    "Trade",
    "Geopolitics",
    "Energy",
    "Technology",
]

