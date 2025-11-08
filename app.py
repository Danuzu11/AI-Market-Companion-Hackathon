
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import requests

# Importación de librerías de LangChain
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

# Función para cargar las series de FRED (FRED API Key) descargando observaciones entre dos fechas.
@st.cache_data(show_spinner=False)
def load_fred_series(
    series_id: str,
    api_key: str,
    start: datetime,
    end: datetime,
    frequency: str,
) -> pd.DataFrame:

    # URL base de la API de FRED
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    # Parámetros de la solicitud
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "observation_start": start.strftime("%Y-%m-%d"),
        "observation_end": end.strftime("%Y-%m-%d"),
        "file_type": "json",
        "frequency": frequency,
    }

    # Realizar la solicitud a la API de FRED
    response = requests.get(base_url, params=params, timeout=15)
    
    # Verificar si la solicitud fue exitosa
    response.raise_for_status()
    data = response.json()
    observations = data.get("observations", [])
    df = pd.DataFrame(observations)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).sort_values("date")

    print("DataFrame cargado desde FRED:")
    print(df)
    return df

# Funcion para normalizar objetos date/datetime en datetime
def ensure_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())

# Funcion para formatear los valores de las series
def format_value(value: float, value_format: str) -> str:
    if value_format == "percent":
        return f"{value:.2f}%"
    if value_format == "billions":
        return f"${value:,.1f}B"
    if value_format == "index":
        return f"{value:.2f}"
    return f"{value:,.2f}"


def build_series_summary(name: str, metadata: Dict[str, str], df: pd.DataFrame) -> str:
    latest = df.iloc[-1]
    summary = (
        f"{name} ({metadata['series_id']}): valor {format_value(latest['value'], metadata['value_format'])} "
        f"a {latest['date'].date()}."
    )
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
    summary += f" {metadata['description']}"
    return summary


def compute_metric_snapshot(
    name: str, metadata: Dict[str, str], df: pd.DataFrame
) -> Dict[str, str]:
    if df.empty:
        return {}
    latest = df.iloc[-1]
    snapshot = {
        "title": name,
        "value": format_value(latest["value"], metadata["value_format"]),
        "date": latest["date"].date().isoformat(),
        "description": metadata["description"],
    }
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

# Configuración de la página
st.set_page_config(
    page_title="AI Market Companion para el S&P 500",
    page_icon="🤖",
    layout="wide",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        width: 550px !important;
        padding-right: 1rem;
        background-color: #111827;
    }
    [data-testid="stSidebar"] * {
        font-size: 15px;
    }
    .metric-card {
        padding: 1.25rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #f9fafb;
    }
    .metric-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #93c5fd;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .metric-delta {
        font-size: 0.85rem;
        opacity: 0.85;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Título de la aplicación
st.title("AI Market Companion :brain:")

# Sidebar de la aplicación
with st.sidebar:
    st.title("🧭 Panel de Control")
    st.caption("Configura las consultas macroeconómicas que alimentarán al analista.")

    with st.form("fred_controls"):
        date_range = st.date_input(
            "Rango de análisis",
            value=(
                (datetime.now() - timedelta(days=180)).date(),
                datetime.now().date(),
            ),
        )
        frequency = st.selectbox(
            "Frecuencia de datos",
            options=[("d", "Diaria"), ("w", "Semanal"), ("m", "Mensual"), ("q", "Trimestral")],
            index=2,
            format_func=lambda option: option[1],
        )

        st.divider()
        
        st.markdown("**Conecta FRED**")
        manual_context = st.text_area(
            "Notas internas del equipo (opcional)",
            value=st.session_state.get("manual_notes", ""),
            height=150,
        )
        fred_api_key = st.text_input("API key de FRED", type="password")
        default_series = st.session_state.get(
            "fred_selected", list(FRED_SERIES.keys())[:2]
        )
        selected_series = st.multiselect(
            "Series a consultar",
            options=list(FRED_SERIES.keys()),
            default=default_series,
        )
        st.session_state.fred_selected = selected_series

        submitted = st.form_submit_button("Actualizar datos macro")
    fred_refresh = submitted
    if submitted:
        st.session_state["manual_notes"] = manual_context
manual_notes = st.session_state.get("manual_notes", "")

# Descripción en el chat de la aplicación
st.write("¡Bienvenido al **Analista Macroeconómico para el S&P 500**! 📊")
st.write(
    "Proporciona noticias, datos o preguntas económicas, y la IA inferirá el **impacto potencial** en el índice S&P 500"
)
st.caption(
    "Esta demostración utiliza un modelo de lenguaje avanzado para **simular el análisis** de un experto, basándose en el contexto económico global. "
)

if manual_notes.strip():
    with st.expander("Notas internas del equipo"):
        st.write(manual_notes)

# Estado inicial para los datos de FRED
fred_data_state = st.session_state.setdefault("fred_data", {})
fred_context_lines: List[str] = st.session_state.setdefault(
    "fred_context_lines", []
)

start_dt = ensure_datetime(date_range[0])
end_dt = ensure_datetime(date_range[1])
frequency_code = frequency[0] if isinstance(frequency, tuple) else frequency

if fred_refresh:
    if not fred_api_key:
        st.warning("Ingresa tu API Key de FRED para descargar datos.")
    elif not selected_series:
        st.info("Selecciona al menos una serie económica de FRED.")
    else:
        print(
            f"[FRED] Solicitando series {selected_series} desde {start_dt.date()} hasta {end_dt.date()}"
        )
        new_data = {}
        new_context = []
        feedback_messages: List[tuple[str, str]] = []
        
        with st.spinner("Descargando series de FRED..."):
            for series_name in selected_series:
                metadata = FRED_SERIES[series_name]
                try:
                    print(
                        f"[FRED] Descargando {metadata['series_id']} ({series_name})..."
                    )
                    df = load_fred_series(
                        metadata["series_id"],
                        fred_api_key,
                        start_dt,
                        end_dt,
                        frequency_code,
                    )
                    print(
                        f"[FRED] {metadata['series_id']} -> {len(df)} observaciones recibidas."
                    )
                except requests.HTTPError as http_err:
                    response = getattr(http_err, "response", None)
                    error_detail = ""
                    user_message = (
                        f"FRED rechazó la serie {series_name}. "
                        "Revisa la clave o los parámetros."
                    )
                    if response is not None:
                        error_detail = response.text
                        try:
                            payload = response.json()
                        except ValueError:
                            payload = {}
                        error_msg = payload.get("error_message") or payload.get(
                            "message", ""
                        )
                        if error_msg:
                            error_detail = error_msg
                        if "api_key" in error_detail.lower():
                            user_message = (
                                "La API key de FRED no tiene el formato correcto "
                                "(32 caracteres alfanuméricos en minúscula). "
                                "Solicita o copia nuevamente la clave desde FRED."
                            )
                    feedback_messages.append(("error", user_message))
                    print(
                        f"[FRED] Error HTTP en {metadata['series_id']}: {http_err} | {error_detail}"
                    )
                    continue
                except requests.RequestException as req_err:
                    msg = f"Fallo de red al consultar {series_name}: {req_err}"
                    feedback_messages.append(("error", msg))
                    print(
                        f"[FRED] Error de red en {metadata['series_id']}: {req_err}"
                    )
                    continue
                new_data[series_name] = {"meta": metadata, "data": df}
                if not df.empty:
                    new_context.append(
                        build_series_summary(series_name, metadata, df)
                    )
                    print(f"[FRED] Resumen generado: {new_context[-1]}")
                else:
                    feedback_messages.append(
                        (
                            "info",
                            f"No hay observaciones disponibles para {series_name} en el rango seleccionado.",
                        )
                    )
                    print(
                        f"[FRED] Serie vacía para {metadata['series_id']} en el rango seleccionado."
                    )
        if new_data:
            st.session_state.fred_data = new_data
            st.session_state.fred_context_lines = new_context
            fred_data_state = new_data
            fred_context_lines = new_context
            st.session_state.fred_feedback = feedback_messages
            print("[FRED] Series actualizadas en estado de sesión.")
        else:
            st.session_state.fred_feedback = feedback_messages or [
                (
                    "warning",
                    "No se pudieron actualizar las series de FRED con los parámetros proporcionados.",
                )
            ]
            print("[FRED] No se cargaron nuevas series.")
elif "fred_feedback" not in st.session_state:
    st.session_state.fred_feedback = []


# Inicializar Ollama y LangChain
try:
    llm = OllamaLLM(model="mistral")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un analista macroeconómico experto. Analiza el contexto y responde con el impacto en el S&P 500.",
            ),
            (
                "human",
                "Datos Contextuales:\n{context_data}\n\nPregunta o noticia:\n{question}",
            ),
        ]
    )
    chain = prompt | llm | StrOutputParser()
except Exception as e:
    st.error(
        "No se pudo conectar con Ollama ni preparar la cadena. "
        "Asegúrate de que Ollama corre en localhost:11434 y que el modelo existe. "
        f"Detalle: {e}"
    )
    chain = None

context_for_llm = "\n".join(fred_context_lines)
print("[LLM] Contexto preparado para el modelo:")
print(context_for_llm)

st.subheader("Indicadores recientes de FRED")

for level, message in st.session_state.get("fred_feedback", []):
    display_fn = getattr(st, level, st.info)
    display_fn(message)

if fred_data_state:
    snapshots = []
    for series_name, payload in fred_data_state.items():
        metadata = payload["meta"]
        df = payload["data"]
        snapshots.append((series_name, metadata, df, compute_metric_snapshot(series_name, metadata, df)))

    valid_snapshots = [item for item in snapshots if item[3]]
    if valid_snapshots:
        cols = st.columns(min(3, len(valid_snapshots)))
        for idx, (_, _, _, snap) in enumerate(valid_snapshots):
            col = cols[idx % len(cols)]
            with col:
                delta = f"{snap.get('delta_text', '')} {snap.get('delta_pct', '')}".strip()
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-title">{snap['title']}</div>
                        <div class="metric-value">{snap['value']}</div>
                        <div class="metric-delta">{delta} · {snap['date']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    for series_name, metadata, df, _ in snapshots:
        st.markdown(f"### {series_name}")
        st.caption(metadata["description"])
        if df.empty:
            st.info(
                "Sin datos disponibles en el rango seleccionado. Ajusta las fechas o intenta más tarde."
            )
            continue
        display_df = (
            df.set_index("date")[["value"]]
            .rename(columns={"value": series_name})
        )
        st.line_chart(display_df)
        st.caption(build_series_summary(series_name, metadata, df))
else:
    st.info(
        "Utiliza la barra lateral para cargar indicadores de FRED y enriquecer el contexto macroeconómico."
    )

# Inicialización del historial del chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Comencemos el análisis! 👇"}
    ]

# Mostrar mensajes del chat desde el historial en la aplicación
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Aceptar entrada del usuario
if question := st.chat_input("¿Qué noticia económica quieres analizar?"):

    # Añadir mensaje del usuario al historial del chat
    st.session_state.messages.append({"role": "user", "content": question})
    
    # Mostrar mensaje del usuario en el contenedor de mensajes del chat
    with st.chat_message("user"):
        st.markdown(question)

    # Mostrar respuesta del asistente en el contenedor de mensajes del chat
    with st.chat_message("assistant"):

        # Crear un contenedor vacío para mostrar la respuesta del asistente
        message_placeholder = st.empty()

        # Inicializar la respuesta del asistente como una cadena vacía
        full_response = ""

        # Verificar si el modelo está disponible
        if chain is None:

            # Mostrar mensaje de error si el modelo no está disponible
            full_response = (
                "El modelo no está disponible en este momento. "
                "Revisa la conexión con Ollama."
            )

            # Mostrar mensaje de error si el modelo no está disponible
            message_placeholder.markdown(full_response)
        elif not context_for_llm.strip():
            full_response = (
                "Aún no se han cargado datos desde FRED. "
                "Introduce tu API key, selecciona series y pulsa 'Actualizar datos de FRED' antes de consultar."
            )
            message_placeholder.markdown(full_response)
        else:
            # Intentar generar la respuesta del asistente
            try:
                # Generar la respuesta del asistente en chunks
                for chunk in chain.stream(
                    {"context_data": context_for_llm, "question": question}
                ):
                    # print(f"[LLM] Chunk recibido: {chunk!r}")
                    full_response += chunk
                    message_placeholder.markdown(full_response + " |")

                message_placeholder.markdown(full_response)
                print("[LLM] Respuesta final del modelo:")
                print(full_response)
                
            except Exception as e:

                # Mostrar mensaje de error si ocurrió un problema al generar la respuesta
                full_response = (
                    "Ocurrió un problema al generar la respuesta. "
                    f"Detalle: {e}"
                )

                # Mostrar mensaje de error si ocurrió un problema al generar la respuesta
                message_placeholder.markdown(full_response)

    # Añadir respuesta del asistente al historial del chat
    st.session_state.messages.append(
        {"role": "assistant", "content": full_response}
    )



