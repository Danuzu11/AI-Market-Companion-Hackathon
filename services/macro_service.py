from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests

from config.data_sources import REGIONAL_MACRO_REGIONS
from core.models import SourceResult


def fetch_eodhd_macro(
    regions: Optional[Iterable[str]] = None,
    api_key: Optional[str] = None,
) -> SourceResult:
    """Obtiene datos macroeconómicos usando EODHD"""
    api_key = api_key or os.getenv("EODHD_API_KEY", "")
    if not api_key:
        result = SourceResult()
        result.feedback.append(
            ("warning", "API key de EODHD no configurada. Usa la variable EODHD_API_KEY en .env")
        )
        return result

    selected = list(regions) if regions else list(REGIONAL_MACRO_REGIONS.keys())
    result = SourceResult()
    tables: Dict[str, pd.DataFrame] = {}
    
    # Símbolos de índices principales por región
    symbols_map = {
        "asia": ["SPY.US", "FXI.US"],  # S&P 500 ETF, China Large-Cap ETF
        "australia": ["EWA.US"],  # Australia ETF
        "europe": ["VGK.US", "EWG.US"],  # Europe ETF, Germany ETF
    }
    
    for region_id in selected:
        symbols = symbols_map.get(region_id, ["SPY.US"])
        region_data = []
        
        for symbol in symbols:
            url = f"https://eodhd.com/api/eod/{symbol}"
            params = {
                "api_token": api_key,
                "fmt": "json",
                "period": "d",
                "order": "d",
                "from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "to": datetime.now().strftime("%Y-%m-%d"),
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                    previous = data[1] if len(data) > 1 else latest
                    
                    current_price = latest.get("close", 0)
                    previous_price = previous.get("close", 0)
                    change = current_price - previous_price
                    change_pct = (change / previous_price * 100) if previous_price > 0 else 0
                    
                    indicator_name = f"{symbol} Price"
                    signal = "Neutral"
                    if change_pct > 1:
                        signal = "Positive momentum"
                    elif change_pct < -1:
                        signal = "Negative pressure"
                    
                    region_data.append({
                        "indicator": indicator_name,
                        "current": round(current_price, 2),
                        "previous": round(previous_price, 2),
                        "units": "USD",
                        "date": latest.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "signal": signal,
                    })
                    
            except requests.RequestException as e:
                result.feedback.append(
                    ("warning", f"Error al obtener datos de EODHD para {symbol}: {str(e)}")
                )
                continue
        
        if region_data:
            label = REGIONAL_MACRO_REGIONS.get(region_id, region_id.title())
            df = pd.DataFrame(region_data)
            tables[region_id] = df
            
            for row in region_data:
                diff = row["current"] - row["previous"]
                diff_text = f" (Δ {diff:+.2f} {row['units']})"
                
                result.context_lines.append(
                    f"{label}: {row['indicator']} {row['current']} {row['units']}{diff_text}. {row['signal']}"
                )
    
    if tables:
        result.extra["macro_tables"] = tables
    
    if not result.context_lines:
        result.feedback.append(
            ("info", "No se encontraron datos macroeconómicos para las regiones seleccionadas.")
        )
    
    return result


def fetch_regional_macro(
    regions: Optional[Iterable[str]] = None,
    api_key: Optional[str] = None,
) -> SourceResult:
    """
    Función principal para obtener datos macroeconómicos regionales.
    Usa EODHD por defecto.
    """
    return fetch_eodhd_macro(regions, api_key)

