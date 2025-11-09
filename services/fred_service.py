# Aqui sacamos las funciones para interactuar con FRED
from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests
import streamlit as st

from config.data_sources import FRED_SERIES
from core.models import SourceResult, TimeSeriesPayload


def ensure_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def format_value(value: float, value_format: str) -> str:
    if value_format == "percent":
        return f"{value:.2f}%"
    if value_format == "billions":
        return f"${value:,.1f}B"
    if value_format == "index":
        return f"{value:.2f}"
    return f"{value:,.2f}"


@st.cache_data(show_spinner=False)
def load_fred_series(
    series_id: str,
    api_key: str,
    start: datetime,
    end: datetime,
    frequency: str,
) -> pd.DataFrame:

    base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    # Parámetros de la consulta
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "observation_start": start.strftime("%Y-%m-%d"),
        "observation_end": end.strftime("%Y-%m-%d"),
        "file_type": "json",
        "frequency": frequency,
    }
    # Realizar la consulta a FRED
    response = requests.get(base_url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    observations = data.get("observations", [])
    df = pd.DataFrame(observations)

    if df.empty:
        return df

    # Convertir la columna de fecha a datetime y la columna de valor a numérico
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Dropna es para eliminar las filas con valores NaN
    df = df.dropna(subset=["value"]).sort_values("date")

    return df


def build_series_summary(name: str, metadata: Dict[str, str], df: pd.DataFrame) -> str:
    # Obtener el último valor y la fecha de la serie
    latest = df.iloc[-1]

    # Construir el resumen de la serie
    summary = (
        f"{name} ({metadata['series_id']}): valor "
        f"{format_value(latest['value'], metadata['value_format'])} "
        f"a {latest['date'].strftime('%d/%m/%Y')}."
    )
    # Si hay más de un dato, calcular el cambio desde el dato previo
    if len(df) > 1:
        previous = df.iloc[-2]
        diff = latest["value"] - previous["value"]
        pct = (
            (diff / previous["value"] * 100)
            if previous["value"] not in (0, None)
            else None
        )
        diff_text = format_value(diff, metadata["value_format"])
        if pct is not None:
            summary += f" Cambio desde el dato previo: {diff_text} ({pct:+.2f}%)."
        else:
            summary += f" Cambio desde el dato previo: {diff_text}."
    # Añadir la descripción de la serie
    summary += f" {metadata['description']}"

    # Con esto retornamos el resumen histórico de la serie
    return summary


def compute_metric_snapshot(
    name: str, metadata: Dict[str, str], df: pd.DataFrame
) -> Dict[str, str]:

    if df.empty:
        return {}

    # Obtener el último valor y la fecha de la serie
    latest = df.iloc[-1]
    # Construir el snapshot de la serie
    snapshot = {
        "title": name,
        "value": format_value(latest["value"], metadata["value_format"]),
        "date": latest["date"].strftime("%d/%m/%Y"),
        "description": metadata["description"],
    }
    # Si hay más de un dato, calcular el cambio desde el dato previo
    if len(df) > 1:
        
        previous = df.iloc[-2]
        diff = latest["value"] - previous["value"]
        pct = (
            (diff / previous["value"] * 100)
            if previous["value"] not in (0, None)
            else None
        )
        snapshot["delta_text"] = format_value(diff, metadata["value_format"])
        snapshot["delta_pct"] = f"{pct:+.2f}%" if pct is not None else ""
    return snapshot

def collect_fred_data(
    selected_series: List[str],
    api_key: str,
    start_dt: datetime,
    end_dt: datetime,
    frequency_code: str,
) -> SourceResult:
    result = SourceResult()

    if not selected_series:
        result.feedback.append(
            ("info", "Selecciona al menos una serie económica de FRED.")
        )
        return result
    
    # Recorrer las series seleccionadas
    for series_name in selected_series:
        metadata = FRED_SERIES[series_name]
        try:
            # Cargar los datos de la serie de FRED
            df = load_fred_series(
                metadata["series_id"],
                api_key,
                start_dt,
                end_dt,
                frequency_code,
            )

        # Si hay un error, añadir un mensaje de error de la serie seleccionada
        except requests.HTTPError as http_err:
            user_message = (
                f"FRED rechazó la serie {series_name}. "
                "Revisa la clave o los parámetros."
            )
            response = getattr(http_err, "response", None)
            error_detail = ""

            # Si hay una respuesta, añadir el detalle del error
            if response is not None:
                try:
                    error_payload = response.json()
                except ValueError:
                    error_payload = {}
                error_detail = (
                    error_payload.get("error_message")
                    or error_payload.get("message")
                    or getattr(response, "text", "")
                )
                if "api_key" in str(error_detail).lower():
                    user_message = (
                        "La API key de FRED no tiene el formato correcto "
                        "(32 caracteres alfanuméricos en minúscula). "
                        "Solicita o copia nuevamente la clave desde FRED."
                    )
            result.feedback.append(("error", user_message))
            continue

        # Si hay un error de red, añadir un mensaje de error
        except requests.RequestException as req_err:
            result.feedback.append(
                (
                    "error",
                    f"Fallo de red al consultar {series_name}: {req_err}",
                )
            )
            continue

        # Crear el payload con los metadatos y los datos de la serie
        payload = TimeSeriesPayload(metadata=metadata, frame=df)
        result.timeseries[series_name] = payload

        # Si no hay datos, añadir un mensaje de observacion
        if df.empty:
            result.feedback.append(
                (
                    "info",
                    f"No hay observaciones disponibles para {series_name} en el rango seleccionado.",
                )
            )
            continue

        # Construir el resumen de la serie
        summary = build_series_summary(series_name, metadata, df)
        # Añadir el resumen al resultado
        result.context_lines.append(summary)

    # Si no hay series y no hay feedback, añadir un mensaje de advertencia
    if not result.timeseries and not result.feedback:
        result.feedback.append(
            (
                "warning",
                "No se pudieron actualizar las series de FRED con los parámetros proporcionados.",
            )
        )

    return result

