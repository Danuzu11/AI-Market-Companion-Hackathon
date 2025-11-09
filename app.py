import os
from datetime import datetime, timedelta
import time
from typing import List

import streamlit as st
from dotenv import load_dotenv

from config.data_sources import (
    DEFAULT_FRED_RANGE_DAYS,
    DEFAULT_FRED_SELECTION,
    FRED_SERIES,
    NEWS_CATEGORIES,
    REGIONAL_MACRO_REGIONS,
)
from core.context_builder import compose_context
from core.source_registry import SOURCE_REGISTRY, SourceConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

from services.fred_service import (
    compute_metric_snapshot,
    ensure_datetime,
    build_series_summary,
)

# Sacamos las API keys de los archivos .env
load_dotenv()
# DEFAULT_FRED_API_KEY = os.getenv("FRED_API_KEY", "")
# DEFAULT_NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
# DEFAULT_EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")

DEFAULT_FRED_API_KEY = "50a935159ab3675d78c5af42132e2700"
# DEFAULT_NEWSAPI_KEY = "43bc8d4c74cf4d089bfa2970df75ba62"
# DEFAULT_EODHD_API_KEY = "690f6492e73213.87491169"
DEFAULT_NEWSAPI_KEY = "11cffdcf1802449cab0ff5ddc30ad92d"
DEFAULT_EODHD_API_KEY = "6910928b7e9373.87218035"

# Configuración de la página
st.set_page_config(
    page_title="EcoAsist · Analítica Macro S&P 500",
    page_icon="🌐",
    layout="wide",
)

# Estilos
st.markdown(
    """
    <style>
    body {
        background: radial-gradient(circle at top left, rgba(63,94,251,0.15), transparent),
                    radial-gradient(circle at bottom right, rgba(252,70,107,0.12), transparent),
                    #020617;
        color: #e5e7eb;
        overflow-x: hidden;
    }

    section[data-testid="stSidebar"] {
        width: 700px !important;
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        padding: 1.5rem 1.1rem 2.5rem;
        background: rgba(2,6,23,0.94);
        border-right: 1px solid rgba(148,163,184,0.08);
        z-index: 99;
    }

    section[data-testid="stSidebar"] > div {
        height: 100%;
        overflow-y: auto;
        padding-right: 0.35rem;
    }
    main[data-testid="stAppViewContainer"] {
        margin-left: 700px;
        /* limit main content width so chat area is less wide */
        max-width: calc(100% - 700px);
    }
    main[data-testid="stAppViewContainer"] .block-container {
        padding-left: 2.4rem;
        padding-right: 2.4rem;
        max-width: 100%;
    }
    .main-card,

    .metric-card {
        padding: 1.35rem;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(30,64,175,0.55), rgba(15,23,42,0.8));
        border: 1px solid rgba(148,163,184,0.15);
        color: #f8fafc;
        box-shadow: 0 20px 40px -30px rgba(29,78,216,0.6);
        margin-bottom: 0.9rem;
    }

    .main-card { margin-top: 8px; }
    .main-card .subtitle { color: #9ca3af; font-size: 0.95rem; margin-top:6px }
    .main-card .intro-grid { display:flex; gap:18px; margin-top:12px }
    .main-card .intro-grid .item { flex:1; background: rgba(255,255,255,0.02); padding:10px; border-radius:8px; color:#cbd5e1 }
    .metric-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #bfdbfe;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .metric-value {
        font-size: 1.7rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    .metric-delta {
        font-size: 0.85rem;
        opacity: 0.85;
        color: rgba(226,232,240,0.95);
    }
    .stButton>button {
        border-radius: 999px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        border: none;
        background: linear-gradient(135deg, rgba(59,130,246,0.85), rgba(14,116,144,0.85));
        color: white;
        box-shadow: 0 15px 30px -20px rgba(56,189,248,0.7);
    }



    .chat-panel .history {
        max-height: 60vh;
        overflow-y: auto;
        padding-bottom: 160px; /* espacio para el input fijo */
    }


    .chat-input-fixed {
        position: fixed;
        left: 700px; /* coincidir con el ancho del sidebar */
        right: 0;
        bottom: 18px;
        z-index: 999;
        padding: 12px 24px;
        background: transparent;
    }

    /* Make chat area visually narrower by capping block-container width */
    main[data-testid="stAppViewContainer"] .block-container {
        max-width: 760px;
    }


    .chat-input-fixed .stTextArea>div, 
    .chat-input-fixed .stForm  {
        max-width: calc(100% - 48px);
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# (Navbar/header/footer left visible by default)

# Configuración de los datos macroeconómicos por defecto
default_start = st.session_state.get(
    "date_range_start",
    (datetime.now() - timedelta(days=DEFAULT_FRED_RANGE_DAYS)).date(),
)
default_end = st.session_state.get("date_range_end", datetime.now().date())
stored_key = st.session_state.get("fred_api_key", DEFAULT_FRED_API_KEY)
default_series = st.session_state.get("fred_selected", DEFAULT_FRED_SELECTION)
include_macro_default = st.session_state.get("include_macro", True)
macro_regions_default = st.session_state.get(
    "macro_regions", list(REGIONAL_MACRO_REGIONS.keys())
)
include_news_default = st.session_state.get("include_news", True)
news_regions_default = st.session_state.get(
    "news_regions", list(REGIONAL_MACRO_REGIONS.keys())
)
news_categories_default = st.session_state.get("news_categories", NEWS_CATEGORIES)

# Configuración de la barra lateral y estilos de la misma
with st.sidebar:

    # Sidebar brand header
    st.markdown(
        """
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>
            <div style='font-size:28px;'>📊</div>
            <div>
                <div style='font-size:18px;font-weight:700;margin:0;color:#e6f0ff;'>EcoAsist</div>
                <div style='font-size:12px;color:#9ca3af;margin-top:2px;'>Analítica Macro · S&P 500</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("control_form"):
        st.markdown("<h3 style='margin-top:0;'>⚙ Configuración de fuentes</h3>", unsafe_allow_html=True)
        date_range_input = st.date_input(
            "Rango de análisis",
            value=(default_start, default_end),
            format="DD/MM/YYYY",
        )
        fred_api_key_input = st.text_input(
            "API key de FRED",
            value=stored_key,
            type="password",
            help="Puedes almacenarla en el archivo .env bajo la variable FRED_API_KEY",
        )
        st.caption("Frecuencia: Trimestral (predefinida)")

        st.markdown("### Series de FRED")
        selected_series_input = st.multiselect(
            "Selecciona indicadores",
            options=list(FRED_SERIES.keys()),
            default=default_series,
        )

        st.markdown("### Cobertura macro regional")
        include_macro_input = st.checkbox(
            "Incluir indicadores regionales", value=include_macro_default
        )
        if include_macro_input:
            eodhd_api_key_input = st.text_input(
                "API key de EODHD",
                value=st.session_state.get("eodhd_api_key", DEFAULT_EODHD_API_KEY),
                type="password",
                help="Puedes almacenarla en el archivo .env bajo la variable EODHD_API_KEY",
            )
            macro_regions_input = st.multiselect(
                "Regiones a monitorear",
                options=list(REGIONAL_MACRO_REGIONS.keys()),
                default=macro_regions_default,
                format_func=lambda key: REGIONAL_MACRO_REGIONS.get(key, key.title()),
            )
        else:
            eodhd_api_key_input = ""
            macro_regions_input = []

        st.markdown("### Noticias públicas")
        include_news_input = st.checkbox(
            "Incluir titulares regionales", value=include_news_default
        )
        
        if include_news_input:
            newsapi_key_input = st.text_input(
                "API key de NewsAPI",
                value=st.session_state.get("newsapi_key", DEFAULT_NEWSAPI_KEY),
                type="password",
                help="Puedes almacenarla en el archivo .env bajo la variable NEWSAPI_KEY",
            )
            news_regions_input = st.multiselect(
                "Regiones para noticias",
                options=list(REGIONAL_MACRO_REGIONS.keys()),
                default=news_regions_default,
                format_func=lambda key: REGIONAL_MACRO_REGIONS.get(key, key.title()),
            )
            news_categories_input = st.multiselect(
                "Categorías",
                options=NEWS_CATEGORIES,
                default=news_categories_default,
            )
        else:
            newsapi_key_input = ""
            news_regions_input = []
            news_categories_input = []
        
        # # Desatiuvamosación de variables para evitar errores porque ApiNews es muy corto el limite    
        # newsapi_key_input = ""
        # news_regions_input = []
        # news_categories_input = []
        
        submitted = st.form_submit_button(
            "Actualizar datos macro", use_container_width=True
        )


# Configuración de la columna principal y estilos de la misma
main_col = st.container()

# Verificación de si se ha actualizado los datos macroeconómicos
if submitted:
    # Actualización de los datos macroeconómicos
    st.session_state["date_range_start"] = date_range_input[0]
    st.session_state["date_range_end"] = date_range_input[1]
    st.session_state["fred_api_key"] = fred_api_key_input
    st.session_state["newsapi_key"] = newsapi_key_input if include_news_input else ""
    st.session_state["eodhd_api_key"] = eodhd_api_key_input if include_macro_input else ""
    st.session_state["fred_selected"] = selected_series_input
    st.session_state["include_macro"] = include_macro_input
    st.session_state["macro_regions"] = macro_regions_input
    st.session_state["include_news"] = include_news_input
    st.session_state["news_regions"] = news_regions_input
    st.session_state["news_categories"] = news_categories_input

# Verificación de si se ha actualizado los datos macroeconómicos y se ha actualizado la configuración
fred_refresh = submitted

# Configuración de los datos macroeconómicos por defecto
date_range = (
    st.session_state.get("date_range_start", default_start),
    st.session_state.get("date_range_end", default_end),
)

fred_api_key = st.session_state.get("fred_api_key", DEFAULT_FRED_API_KEY)
selected_series = st.session_state.get("fred_selected", DEFAULT_FRED_SELECTION)
include_macro = st.session_state.get("include_macro", True)
macro_regions = (
    st.session_state.get("macro_regions", list(REGIONAL_MACRO_REGIONS.keys()))
    if include_macro
    else []
)
include_news = st.session_state.get("include_news", True)
news_regions = (
    st.session_state.get("news_regions", list(REGIONAL_MACRO_REGIONS.keys()))
    if include_news
    else []
)
news_categories = (
    st.session_state.get("news_categories", NEWS_CATEGORIES)
    if include_news
    else []
)

# Configuración de la columna principal y estilos de la misma
with main_col:
    st.markdown(
        """
        <div class="main-card">
            <h2 style="margin-top:0;">📈 EcoAsist · Analítica Macro</h2>
            <div class="subtitle">Bienvenido — sintetizamos indicadores macro, señales regionales y titulares públicos para inferir posibles impactos en el S&P 500.</div>
            <div class="intro-grid">
                <div class="item">
                    <strong>Qué hace</strong>
                    <div>Integra series de FRED, señales regionales y titulares para ofrecer un diagnóstico cuantitativo y cualitativo.</div>
                </div>
                <div class="item">
                    <strong>Cómo usar</strong>
                    <div>Configura tus fuentes en la barra lateral y formula una consulta en el chat. P. ej.: "¿Riesgo de recesión para el próximo trimestre?"</div>
                </div>
                <div class="item">
                    <strong>Limitaciones</strong>
                    <div>Modelo orientativo: revisa las fuentes y toma este análisis como apoyo, no como recomendación de inversión.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    source_results_state = st.session_state.setdefault("source_results", {})
    source_feedback_state = st.session_state.setdefault("source_feedback", {})

    start_dt = ensure_datetime(date_range[0])
    end_dt = ensure_datetime(date_range[1])
    frequency_code = "q"

    if fred_refresh:
        new_results = {}
        new_feedback = {}
        params_by_source = {
            "fred": dict(
                selected_series=selected_series,
                api_key=fred_api_key,
                start_dt=start_dt,
                end_dt=end_dt,
                frequency_code=frequency_code,
            ),
        }
        sources_to_fetch = ["fred"]

        if st.session_state.get("include_macro") and st.session_state.get("macro_regions"):
            params_by_source["macro_regional"] = dict(
                regions=st.session_state["macro_regions"],
                api_key=st.session_state.get("eodhd_api_key", DEFAULT_EODHD_API_KEY),
            )
            sources_to_fetch.append("macro_regional")

        # Disabled NewsAPI backend fetching: keep the sidebar UI for visual purposes
        # but do NOT include it in sources_to_fetch or perform any API calls.
        # if (
        #     st.session_state.get("include_news")
        #     and st.session_state.get("news_regions")
        #     and st.session_state.get("news_categories")
        # ):
        #     params_by_source["news_public"] = dict(
        #         regions=st.session_state["news_regions"],
        #         categories=st.session_state["news_categories"],
        #         api_key=st.session_state.get("newsapi_key", DEFAULT_NEWSAPI_KEY),
        #     )
        #     sources_to_fetch.append("news_public")
        # else:
        params_by_source["news_public"] = dict(regions=[], categories=[], api_key="")

        for source_id in sources_to_fetch:
            config: SourceConfig = SOURCE_REGISTRY[source_id]
            params = params_by_source.get(source_id, {})
            if config.requires_api_key and not params.get("api_key"):
                new_feedback[source_id] = [
                    (
                        "warning",
                        f"Ingrese una API key válida para la fuente {config.label}.",
                    )
                ]
                continue

            with st.spinner(f"Descargando datos de {config.label}..."):
                result = config.fetcher(**params)
            new_results[source_id] = result
            new_feedback[source_id] = result.feedback

        if new_results:
            st.session_state.source_results = new_results
            source_results_state = new_results
        st.session_state.source_feedback = new_feedback
        source_feedback_state = new_feedback

    fred_result = source_results_state.get("fred")
    macro_result = source_results_state.get("macro_regional")
    news_result = source_results_state.get("news_public")

    fred_feedback = source_feedback_state.get("fred", [])
    macro_feedback = source_feedback_state.get("macro_regional", [])
    news_feedback = source_feedback_state.get("news_public", [])

    fred_data_state = fred_result.timeseries if fred_result else {}
    fred_context_lines: List[str] = fred_result.context_lines if fred_result else []
    macro_context_lines: List[str] = macro_result.context_lines if macro_result else []
    news_context_lines: List[str] = news_result.context_lines if news_result else []

    try:
        llm = OllamaLLM(model="mistral")
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Actúas como estratega macro-financiero senior. Combina indicadores de FRED, señales regionales y te llamas EcoAsist "
                    "(Asia, Australia, Europa) y titulares públicos para inferir implicaciones sobre el S&P 500. "
                    "Las noticias incluyen análisis de tendencia de mercado con valores p (político), q (cultural), s (social) "
                    "y una inferencia ALZISTA o BAJISTA con tasa calculada basada en la tabla de verdad. "
                    "Usa esta información para evaluar el impacto potencial en el mercado. "
                    "Solo usa el contexto proporcionado; si falta información, acláralo. "
                    "Responde amablemente y decentemente solo cuando el usuario te lo pida. "
                    "Si saluda, lo saludas amablemente y le dices quién eres. "
                    "SIEMPRE responde en español",
                ),
                (
                    "human",
                    "Contexto agregado:\n{context_data}\n\nConsulta del analista:\n{question}",
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

    # Configuración de los contextos para el LLM
    context_sources = {"FRED (EE.UU.)": fred_context_lines}
    if macro_context_lines:
        context_sources["Indicadores regionales"] = macro_context_lines
    if news_context_lines:
        context_sources["Noticias públicas"] = news_context_lines

    # Configuración de los contextos para el LLM
    context_for_llm = compose_context(context_sources)

    # Configuración de los snapshots para el LLM
    snapshots: List[dict] = []

    # Configuración de las series de FRED para el LLM
    fred_series_blocks = []
    if fred_data_state:
        for series_name, payload in fred_data_state.items():
            metadata = payload.metadata
            df = payload.frame
            series_summary = build_series_summary(series_name, metadata, df)
            fred_series_blocks.append((series_name, metadata, df, series_summary))
            snapshot = compute_metric_snapshot(series_name, metadata, df)
            if snapshot:
                snapshots.append(snapshot)

    macro_tables = macro_result.extra.get("macro_tables", {}) if macro_result else {}
    news_items = news_result.extra.get("news", {}) if news_result else {}

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Listo para analizar. ¿Qué escenario económico quieres explorar? 👇"}
        ]

    st.markdown("#### Indicadores recientes de FRED")
    if fred_feedback:
        for level, message in fred_feedback:
            display_fn = getattr(st, level, st.info)
            display_fn(f"FRED: {message}")
    if snapshots:
        for snap in snapshots:
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
    else:
        st.info("Utiliza la barra lateral para cargar indicadores de FRED.")



    st.markdown("#### Visualizaciones y contexto")
    if fred_series_blocks:
        for series_name, metadata, df, summary_text in fred_series_blocks:
            st.markdown(f"### {series_name}")
            st.caption(metadata["description"])
            if df.empty:
                st.info(
                    "Sin datos disponibles en el rango seleccionado. Ajusta las fechas o intenta más tarde."
                )
            else:
                display_df = df.set_index("date")["value"].to_frame(name=series_name)
                st.line_chart(display_df)
                st.caption(summary_text)
    else:
        st.info("Carga indicadores para visualizar las series de FRED.")

    if macro_feedback:
        for level, message in macro_feedback:
            display_fn = getattr(st, level, st.info)
            display_fn(f"Indicadores regionales: {message}")

    if macro_tables:
        st.markdown("### Indicadores regionales")
        for region_id, table in macro_tables.items():
            label = REGIONAL_MACRO_REGIONS.get(region_id, region_id.title())
            st.markdown(f"#### {label}")
            st.dataframe(table)

    # NewsAPI rendering disabled: backend fetching/commented out.
    # The sidebar still shows visual controls for news, but no requests are made.
    # st.info("Noticias públicas: deshabilitadas en el backend. La UI mantiene controles visuales pero no hay análisis ni llamadas a NewsAPI.")



    # APLICAR EL ESTILO DE PANEL DE CHAT FIJO
    st.markdown("<div class='panel-card chat-panel'>", unsafe_allow_html=True)

    # El historial de mensajes (contenedor que va a SCROLLEAR)
    history_container = st.container()

    # Renderizar el historial DENTRO DE UN DIV DE SCROLL
    # Si hay una transmisión (streaming) en curso, creamos un placeholder
    # para el mensaje assistant en streaming y lo actualizaremos más abajo.
    streaming = st.session_state.get("streaming")
    message_placeholder = None
    with history_container:
        st.markdown("<div class='history'>", unsafe_allow_html=True)
        for i, message in enumerate(st.session_state.messages):
            # Si este mensaje es el que se está transmitiendo, crear placeholder
            if (
                streaming
                and streaming.get("status") == "running"
                and streaming.get("assistant_index") == i
            ):
                with st.chat_message("assistant"):
                    # render current content (may be empty) into a placeholder
                    message_placeholder = st.empty()
                    message_placeholder.markdown(message.get("content", ""))
            else:
                with st.chat_message(message.get("role", "assistant")):
                    st.markdown(message.get("content", ""))
        st.markdown("</div>", unsafe_allow_html=True)
    

    # El input del chat (queda fijo abajo)
    st.markdown("<div class='chat-input-fixed'>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        prompt_value = st.text_area(
            "Escribe tu análisis",
            key="chat_prompt",
            height=90,
            label_visibility="collapsed",
            placeholder="Formula tu pregunta aquí...",
        )
        prompt_submitted = st.form_submit_button("Enviar", use_container_width=True)
        
    st.markdown("</div>", unsafe_allow_html=True) # Cierra chat-panel

    # Handle submit: start streaming by appending an empty assistant message
    # and setting a streaming flag in session_state, then rerun so the
    # history is rendered (with a placeholder) before we start the stream.
    if prompt_submitted and prompt_value.strip():
        question = prompt_value.strip()

        st.session_state.setdefault("messages", [])
        # Append user and an empty assistant message
        st.session_state["messages"].append({"role": "user", "content": question})
        st.session_state["messages"].append({"role": "assistant", "content": ""})
        assistant_index = len(st.session_state["messages"]) - 1

        # Mark streaming info so the next rerun will create a placeholder
        st.session_state["streaming"] = {
            "assistant_index": assistant_index,
            "question": question,
            "status": "running",
        }
        st.rerun()

    # If there is a streaming flag and we created a placeholder above,
    # perform the actual streaming here (this runs after the rerun so the
    # placeholder exists in the page and we can update it incrementally).
    streaming = st.session_state.get("streaming")
    if streaming and message_placeholder is not None:
        assistant_index = streaming.get("assistant_index")
        question = streaming.get("question")

        # Safety checks
        if 'chain' not in globals() or chain is None:
            final = "El modelo no está disponible en este momento. Verifica Ollama."
            st.session_state["messages"][assistant_index]["content"] = final
            message_placeholder.markdown(final)
            del st.session_state["streaming"]
            st.rerun()

        if not globals().get("context_for_llm", "").strip():
            final = (
                "Aún no se han cargado datos. Introduce tu API key y pulsa 'Actualizar datos'."
            )
            st.session_state["messages"][assistant_index]["content"] = final
            message_placeholder.markdown(final)
            del st.session_state["streaming"]
            st.rerun()

        # Stream chunks and update both the placeholder and session_state
        try:
            if hasattr(chain, 'stream'):
                for chunk in chain.stream({"context_data": context_for_llm, "question": question}):
                    # append chunk to message content
                    cur = st.session_state["messages"][assistant_index].get("content", "")
                    cur += chunk
                    st.session_state["messages"][assistant_index]["content"] = cur
                    # show interim with cursor
                    message_placeholder.markdown(cur + " ▌")
                    # small sleep to allow frontend to update smoothly
                    time.sleep(0.05)
            elif hasattr(chain, 'run'):
                final = chain.run({"context_data": context_for_llm, "question": question})
                st.session_state["messages"][assistant_index]["content"] = final
                message_placeholder.markdown(final)
            else:
                final = "(No hay método válido para invocar al LLM)"
                st.session_state["messages"][assistant_index]["content"] = final
                message_placeholder.markdown(final)
        except Exception as e:
            final = f"Ocurrió un problema al generar la respuesta: {e}"
            st.session_state["messages"][assistant_index]["content"] = final
            message_placeholder.markdown(final)

        # Finish streaming: remove flag and rerun to render final state normally
        if "streaming" in st.session_state:
            del st.session_state["streaming"]
        st.rerun()

        