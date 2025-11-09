
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

import pandas as pd
import requests
from dotenv import load_dotenv

# Importación de Google Generative AI (Gemini)
import google.generativeai as genai

# Cargar variables de entorno desde archivo .env
load_dotenv()

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
    "Tipo de cambio real efectivo - Zona Euro (RBEREA)": {
        "series_id": "RBEREA",
        "value_format": "index",
        "description": "Tipo de cambio real efectivo amplio para la Zona Euro.",
    },
    "Tipo de cambio real efectivo - Japón (RBERJP)": {
        "series_id": "RBERJP",
        "value_format": "index",
        "description": "Tipo de cambio real efectivo amplio para Japón.",
    },
    "Tipo de cambio USD/EUR (DEXUSEU)": {
        "series_id": "DEXUSEU",
        "value_format": "index",
        "description": "Dólares estadounidenses a tipo de cambio al contado del Euro.",
    },
    "Tipo de cambio real efectivo - Hong Kong (RBERHK)": {
        "series_id": "RBERHK",
        "value_format": "index",
        "description": "Tipo de cambio real efectivo amplio para Hong Kong SAR.",
    },
}

# Queries de noticias para NewsAPI
NEWS_QUERIES = [
    # Macroeconomía
    '("GDP" OR "economic growth" OR "recession") AND ("Australia" OR "Europe" OR "Asia")',
    '("inflation" OR "CPI" OR "PPI") AND ("Australia" OR "Europe" OR "Asia")',
    '("interest rate" OR "monetary policy" OR "central bank") AND ("RBA" OR "ECB" OR "BoJ" OR "Australia" OR "Europe" OR "Asia")',
    '("unemployment" OR "jobless rate" OR "labor market") AND ("Australia" OR "Europe" OR "Asia")',
    '("PMI" OR "manufacturing index" OR "services index") AND ("Australia" OR "Europe" OR "Asia")',
    # Mercados financieros
    '("stock market" OR "equities" OR "share prices") AND ("Australia" OR "Europe" OR "Asia")',
    '("bond yields" OR "sovereign debt" OR "treasury rates") AND ("Australia" OR "Europe" OR "Asia")',
    '("currency exchange" OR "forex" OR "FX rates") AND ("Australia" OR "Europe" OR "Asia")',
    '("commodities" OR "oil prices" OR "gold" OR "metals" OR "energy prices") AND ("Australia" OR "Europe" OR "Asia")',
    # Política y geopolítica
    '("election" OR "government change" OR "political unrest") AND ("Australia" OR "Europe" OR "Asia")',
    '("trade deal" OR "tariffs" OR "WTO" OR "trade dispute") AND ("Australia" OR "Europe" OR "Asia")',
    '("sanctions" OR "geopolitical risk" OR "international conflict") AND ("Australia" OR "Europe" OR "Asia")',
    # Empresas y sectores clave
    '("earnings report" OR "profit warning" OR "revenue miss") AND ("Australia" OR "Europe" OR "Asia")',
    '("merger" OR "acquisition" OR "M&A") AND ("Australia" OR "Europe" OR "Asia")',
    '("technology" OR "semiconductor" OR "finance" OR "energy" OR "healthcare") AND ("Australia" OR "Europe" OR "Asia")',
    # Eventos de alto impacto
    '("financial crisis" OR "banking collapse" OR "credit event") AND ("Australia" OR "Europe" OR "Asia")',
    '("pandemic" OR "natural disaster" OR "emergency") AND ("Australia" OR "Europe" OR "Asia")',
    '("quantitative easing" OR "QE" OR "tapering") AND ("RBA" OR "ECB" OR "BoJ" OR "Australia" OR "Europe" OR "Asia")',
]

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

# Función para cargar noticias desde NewsAPI
@st.cache_data(show_spinner=False)
def load_news_from_newsapi(
    api_key: str,
    queries: List[str],
    from_date: datetime,
    to_date: datetime,
    max_articles_per_query: int = 10,
) -> List[Dict]:
    """
    Carga noticias desde NewsAPI usando múltiples queries.
    Retorna una lista de artículos únicos ordenados por fecha.
    """
    base_url = "https://newsapi.org/v2/everything"
    all_articles = []
    seen_urls = set()
    
    for query in queries:
        params = {
            "q": query,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_articles_per_query,
            "apiKey": api_key,
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get("articles", [])
            for article in articles:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(article)
            
            print(f"[NewsAPI] Query '{query[:50]}...' -> {len(articles)} artículos encontrados")
        except requests.HTTPError as http_err:
            response = getattr(http_err, "response", None)
            error_detail = ""
            if response is not None:
                try:
                    payload = response.json()
                    error_detail = payload.get("message", "")
                except ValueError:
                    error_detail = response.text
            print(f"[NewsAPI] Error HTTP en query '{query[:50]}...': {http_err} | {error_detail}")
            continue
        except requests.RequestException as req_err:
            print(f"[NewsAPI] Error de red en query '{query[:50]}...': {req_err}")
            continue
    
    # Ordenar por fecha de publicación (más recientes primero)
    all_articles.sort(
        key=lambda x: x.get("publishedAt", ""),
        reverse=True
    )
    
    print(f"[NewsAPI] Total de artículos únicos: {len(all_articles)}")
    return all_articles

def build_news_summary(articles: List[Dict], max_articles: int = 20) -> str:
    """
    Construye un resumen de noticias para el contexto del LLM.
    """
    if not articles:
        return "No hay noticias disponibles para el período seleccionado."
    
    summary_lines = ["=== NOTICIAS RECIENTES DE ASIA, AUSTRALIA Y EUROPA ===\n"]
    
    for idx, article in enumerate(articles[:max_articles], 1):
        title = article.get("title", "Sin título")
        description = article.get("description", "")
        source = article.get("source", {}).get("name", "Fuente desconocida")
        published = article.get("publishedAt", "")
        
        summary_lines.append(f"{idx}. [{source}] {title}")
        if description:
            summary_lines.append(f"   {description[:200]}...")
        if published:
            summary_lines.append(f"   Publicado: {published[:10]}")
        summary_lines.append("")
    
    return "\n".join(summary_lines)

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
    st.caption("Configura las fuentes de datos que alimentarán al analista.")

    with st.form("data_controls"):
        # Rango de análisis: 1 semana por defecto
        date_range = st.date_input(
            "Rango de análisis (última semana)",
            value=(
                (datetime.now() - timedelta(days=7)).date(),
                datetime.now().date(),
            ),
        )
        frequency = st.selectbox(
            "Frecuencia de datos FRED",
            options=[("d", "Diaria"), ("w", "Semanal"), ("m", "Mensual"), ("q", "Trimestral")],
            index=0,
            format_func=lambda option: option[1],
        )

        st.divider()
        
        st.markdown("**Conecta FRED**")
        # Cargar desde .env o usar input del sidebar
        default_fred_key = os.getenv("FRED_API_KEY", "")
        fred_api_key = st.text_input(
            "API key de FRED", 
            type="password", 
            key="fred_key",
            value=st.session_state.get("fred_api_key", default_fred_key)
        )
        if fred_api_key:
            st.session_state.fred_api_key = fred_api_key
        st.caption("Obtén tu clave en fred.stlouisfed.org o configúrala en .env")
        
        default_series = st.session_state.get(
            "fred_selected", list(FRED_SERIES.keys())
        )
        selected_series = st.multiselect(
            "Series económicas a consultar",
            options=list(FRED_SERIES.keys()),
            default=default_series,
        )
        st.session_state.fred_selected = selected_series

        st.divider()
        
        st.markdown("**Conecta NewsAPI**")
        # Cargar desde .env o usar input del sidebar
        default_news_key = os.getenv("NEWS_API_KEY", "")
        news_api_key = st.text_input(
            "API key de NewsAPI", 
            type="password", 
            key="news_key",
            value=st.session_state.get("news_api_key", default_news_key)
        )
        if news_api_key:
            st.session_state.news_api_key = news_api_key
        st.caption("Obtén tu clave en newsapi.org o configúrala en .env")

        st.divider()
        
        st.markdown("**Conecta Google Gemini**")
        # Cargar desde .env o usar input del sidebar
        default_gemini_key = os.getenv("GEMINI_API_KEY", "")
        gemini_api_key_input = st.text_input(
            "API key de Google Gemini", 
            type="password", 
            key="gemini_key",
            value=st.session_state.get("gemini_api_key", default_gemini_key)
        )
        if gemini_api_key_input:
            st.session_state.gemini_api_key = gemini_api_key_input
        st.caption("Obtén tu clave en https://aistudio.google.com/app/apikey o configúrala en .env")

        submitted = st.form_submit_button("🔄 Actualizar datos y analizar")
    
    fred_refresh = submitted
    news_refresh = submitted
    
    # Obtener API keys: primero del session_state, luego del .env
    fred_api_key = st.session_state.get("fred_api_key", os.getenv("FRED_API_KEY", ""))
    news_api_key = st.session_state.get("news_api_key", os.getenv("NEWS_API_KEY", ""))
    gemini_api_key = st.session_state.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))

# Descripción de la aplicación
st.write("¡Bienvenido al **Analista Macroeconómico para el S&P 500**! 📊")
st.write(
    "Esta aplicación analiza automáticamente **noticias y datos económicos de Asia, Australia y Europa** "
    "para inferir el **impacto potencial** en el índice S&P 500."
)
st.caption(
    "El sistema utiliza IA para analizar noticias recientes y datos macroeconómicos, "
    "prediciendo si el impacto será **positivo** (subida), **negativo** (bajada) o **neutral** en el S&P 500."
)

# Estado inicial para los datos de FRED y noticias
fred_data_state = st.session_state.setdefault("fred_data", {})
fred_context_lines: List[str] = st.session_state.setdefault(
    "fred_context_lines", []
)
news_articles_state = st.session_state.setdefault("news_articles", [])
news_summary_state = st.session_state.setdefault("news_summary", "")

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

# Cargar noticias desde NewsAPI
if news_refresh:
    if not news_api_key:
        st.warning("Ingresa tu API Key de NewsAPI para descargar noticias.")
    else:
        print(f"[NewsAPI] Solicitando noticias desde {start_dt.date()} hasta {end_dt.date()}")
        feedback_messages_news: List[tuple[str, str]] = []
        
        with st.spinner("Descargando noticias desde NewsAPI..."):
            try:
                articles = load_news_from_newsapi(
                    news_api_key,
                    NEWS_QUERIES,
                    start_dt,
                    end_dt,
                    max_articles_per_query=10,
                )
                if articles:
                    st.session_state.news_articles = articles
                    st.session_state.news_summary = build_news_summary(articles, max_articles=30)
                    news_articles_state = articles
                    news_summary_state = st.session_state.news_summary
                    feedback_messages_news.append(("success", f"Se encontraron {len(articles)} noticias relevantes."))
                    print(f"[NewsAPI] {len(articles)} noticias cargadas exitosamente.")
                else:
                    feedback_messages_news.append(("info", "No se encontraron noticias para el período seleccionado."))
                    print("[NewsAPI] No se encontraron noticias.")
            except Exception as e:
                error_msg = f"Error al cargar noticias: {e}"
                feedback_messages_news.append(("error", error_msg))
                print(f"[NewsAPI] Error: {e}")
        
        st.session_state.news_feedback = feedback_messages_news
elif "news_feedback" not in st.session_state:
    st.session_state.news_feedback = []

# Función para generar análisis con Gemini
def generate_analysis_with_gemini(
    api_key: str,
    economic_data: str,
    news_data: str,
) -> Optional[str]:
    """
    Genera análisis usando la API de Gemini directamente.
    Retorna el texto completo del análisis o None si hay error.
    """
    try:
        # Configurar Gemini
        genai.configure(api_key=api_key)
        
        # Seleccionar modelo
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Construir el prompt
        system_prompt = """Eres un analista macroeconómico experto especializado en predecir el impacto de eventos internacionales 
en el mercado estadounidense. Tu tarea es analizar noticias y datos económicos de Asia, Australia y Europa 
para inferir el impacto potencial en el índice S&P 500.

Debes proporcionar:
1. **PREDICCIÓN DE IMPACTO**: Una de estas tres opciones:
   - POSITIVO (subida): El S&P 500 probablemente subirá
   - NEGATIVO (bajada): El S&P 500 probablemente bajará
   - NEUTRAL: El impacto será mínimo o neutral

2. **ANÁLISIS DETALLADO**: Explica tu razonamiento considerando:
   - Cómo los eventos económicos internacionales afectan a las empresas del S&P 500
   - Correlaciones históricas entre mercados globales
   - Impacto en sectores clave (tecnología, finanzas, energía, etc.)
   - Flujos de capital y tipos de cambio
   - Sentimiento del mercado

3. **NIVEL DE CONFIANZA**: Indica qué tan confiado estás en tu predicción (Alto/Medio/Bajo)

Sé específico y fundamenta tu análisis con los datos proporcionados."""

        user_prompt = f"""Datos Macroeconómicos de FRED:
{economic_data}

{news_data}

Analiza estos datos y noticias para predecir el impacto en el S&P 500. 
Proporciona tu predicción (POSITIVO/NEGATIVO/NEUTRAL), análisis detallado y nivel de confianza."""

        # Generar respuesta
        response = model.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )
        
        return response.text
        
    except Exception as e:
        print(f"[Gemini] Error: {e}")
        return None

def stream_analysis_with_gemini(
    api_key: str,
    economic_data: str,
    news_data: str,
):
    """
    Genera análisis usando la API de Gemini con streaming.
    Yield chunks de texto conforme se generan.
    """
    try:
        # Configurar Gemini
        genai.configure(api_key=api_key)
        
        # Seleccionar modelo
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Construir el prompt
        system_prompt = """Eres un analista macroeconómico experto especializado en predecir el impacto de eventos internacionales 
en el mercado estadounidense. Tu tarea es analizar noticias y datos económicos de Asia, Australia y Europa 
para inferir el impacto potencial en el índice S&P 500.

Debes proporcionar:
1. **PREDICCIÓN DE IMPACTO**: Una de estas tres opciones:
   - POSITIVO (subida): El S&P 500 probablemente subirá
   - NEGATIVO (bajada): El S&P 500 probablemente bajará
   - NEUTRAL: El impacto será mínimo o neutral

2. **ANÁLISIS DETALLADO**: Explica tu razonamiento considerando:
   - Cómo los eventos económicos internacionales afectan a las empresas del S&P 500
   - Correlaciones históricas entre mercados globales
   - Impacto en sectores clave (tecnología, finanzas, energía, etc.)
   - Flujos de capital y tipos de cambio
   - Sentimiento del mercado

3. **NIVEL DE CONFIANZA**: Indica qué tan confiado estás en tu predicción (Alto/Medio/Bajo)

Sé específico y fundamenta tu análisis con los datos proporcionados."""

        user_prompt = f"""Datos Macroeconómicos de FRED:
{economic_data}

{news_data}

Analiza estos datos y noticias para predecir el impacto en el S&P 500. 
Proporciona tu predicción (POSITIVO/NEGATIVO/NEUTRAL), análisis detallado y nivel de confianza."""

        # Generar respuesta con streaming
        response = model.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            ),
            stream=True
        )
        
        # Yield chunks conforme se generan
        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        print(f"[Gemini] Error en streaming: {e}")
        yield f"Error al generar análisis: {e}"

# Verificar si Gemini está configurado
gemini_configured = bool(gemini_api_key)

# Preparar contexto para el LLM
economic_context = "\n".join(fred_context_lines) if fred_context_lines else "No hay datos económicos disponibles."
news_context = news_summary_state if news_summary_state else "No hay noticias disponibles para el período seleccionado."

print("[LLM] Contexto económico preparado:")
print(economic_context[:500] + "..." if len(economic_context) > 500 else economic_context)
print("[LLM] Contexto de noticias preparado:")
print(news_context[:500] + "..." if len(news_context) > 500 else news_context)

# Mostrar feedback de FRED y NewsAPI
st.subheader("📊 Indicadores recientes de FRED")

for level, message in st.session_state.get("fred_feedback", []):
    display_fn = getattr(st, level, st.info)
    display_fn(message)

# Mostrar feedback de NewsAPI
if st.session_state.get("news_feedback"):
    st.subheader("📰 Estado de noticias")
    for level, message in st.session_state.get("news_feedback", []):
        display_fn = getattr(st, level, st.info)
        if level == "success":
            # Usar st.success si está disponible, sino st.info
            try:
                st.success(message)
            except:
                st.info(f"✓ {message}")
        else:
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

# Mostrar noticias cargadas
if news_articles_state:
    st.subheader("📰 Noticias recientes de Asia, Australia y Europa")
    with st.expander(f"Ver {len(news_articles_state)} noticias encontradas", expanded=False):
        for idx, article in enumerate(news_articles_state[:20], 1):
            title = article.get("title", "Sin título")
            description = article.get("description", "")
            source = article.get("source", {}).get("name", "Fuente desconocida")
            url = article.get("url", "")
            published = article.get("publishedAt", "")
            
            st.markdown(f"**{idx}. {title}**")
            st.caption(f"Fuente: {source} | Fecha: {published[:10] if published else 'N/A'}")
            if description:
                st.write(description[:300] + "..." if len(description) > 300 else description)
            if url:
                st.markdown(f"[Leer más]({url})")
            st.divider()

# Análisis automático con IA
st.subheader("🤖 Análisis de Impacto en S&P 500")

# Verificar si hay datos suficientes para el análisis
has_economic_data = bool(economic_context and economic_context != "No hay datos económicos disponibles.")
has_news_data = bool(news_context and news_context != "No hay noticias disponibles para el período seleccionado.")

if not has_economic_data and not has_news_data:
    st.info(
        "💡 **Para comenzar el análisis:**\n\n"
        "1. Ingresa tus API keys de FRED y NewsAPI en el panel lateral\n"
        "2. Selecciona las series económicas que deseas analizar\n"
        "3. Haz clic en '🔄 Actualizar datos y analizar'\n\n"
        "El sistema analizará automáticamente los datos y noticias para predecir el impacto en el S&P 500."
    )
elif not gemini_configured:
    st.error(
        "El modelo de IA no está disponible. "
        "Asegúrate de haber ingresado tu API key de Google Gemini en el panel lateral."
    )
else:
    # Realizar análisis automático cuando hay datos
    should_analyze = (fred_refresh or news_refresh) or st.session_state.get("auto_analyze", False)
    
    if should_analyze and (has_economic_data or has_news_data):
        with st.spinner("🤖 Analizando datos y noticias con Gemini..."):
            try:
                analysis_placeholder = st.empty()
                full_analysis = ""
                
                # Generar análisis en streaming con Gemini
                for chunk in stream_analysis_with_gemini(
                    gemini_api_key,
                    economic_context,
                    news_context,
                ):
                    full_analysis += chunk
                    analysis_placeholder.markdown(full_analysis + " |")
                
                analysis_placeholder.markdown(full_analysis)
                
                # Guardar análisis en el estado de sesión
                st.session_state.last_analysis = full_analysis
                st.session_state.auto_analyze = False
                
                print("[Gemini] Análisis completado:")
                print(full_analysis[:500] + "..." if len(full_analysis) > 500 else full_analysis)
                
            except Exception as e:
                error_msg = f"Error al generar el análisis: {e}"
                st.error(error_msg)
                print(f"[Gemini] Error: {e}")
    elif st.session_state.get("last_analysis"):
        # Mostrar último análisis si existe
        st.markdown("### Último análisis realizado:")
        st.markdown(st.session_state.last_analysis)
        if st.button("🔄 Re-analizar con datos actuales"):
            st.session_state.auto_analyze = True
            st.rerun()
    else:
        st.info(
            "Haz clic en '🔄 Actualizar datos y analizar' en el panel lateral "
            "para generar un nuevo análisis basado en los datos más recientes."
        )



