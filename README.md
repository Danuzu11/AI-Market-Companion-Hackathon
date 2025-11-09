# AI Market Companion

Aplicación construida con Streamlit que combina datos macroeconómicos de múltiples fuentes (FRED, EODHD) con noticias en tiempo real (NewsAPI, NewsData.io) y un analista conversacional impulsado por LangChain y modelos servidos por Ollama. Permite a los miembros del equipo explorar indicadores macro clave, generar visualizaciones rápidas, analizar sentimiento de noticias y obtener un juicio cualitativo sobre el posible impacto en el índice S&P 500.

## Características

- **Datos macroeconómicos de FRED**: Series económicas oficiales de Estados Unidos (PIB, desempleo, inflación)
- **Indicadores regionales con EODHD**: Datos de índices financieros y ETFs por región (Asia, Australia, Europa)
- **Noticias en tiempo real**: Integración con NewsAPI.org y NewsData.io para obtener titulares relevantes
- **Análisis de sentimiento**: Procesamiento automático de noticias para determinar sentimiento (positivo/negativo/neutral) basado en análisis político, cultural y social
- **Chat conversacional**: Interfaz de chat con LLM (Mistral vía Ollama) que analiza el contexto consolidado

## Requisitos

- Python 3.10+
- Ollama instalado y ejecutándose en `localhost:11434` con el modelo `mistral` descargado (`ollama pull mistral`)
- Claves de API:
  - **FRED**: Para datos macroeconómicos de Estados Unidos ([obtener aquí](https://fred.stlouisfed.org/docs/api/api_key.html))
  - **NewsAPI**: Para noticias en tiempo real ([obtener aquí](https://newsapi.org/register))
  - **EODHD**: Para datos de índices financieros ([obtener aquí](https://eodhd.com/))

## Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows)
venv\Scripts\activate

# Activar entorno virtual (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con tus claves de API:

```env
FRED_API_KEY=tu_clave_de_fred
NEWSAPI_KEY=tu_clave_de_newsapi
EODHD_API_KEY=tu_clave_de_eodhd
```

**Nota**: También puedes ingresar las claves directamente en la interfaz de Streamlit, pero se recomienda usar el archivo `.env` por seguridad.

## Ejecución

1. **Inicia Ollama** (si no está activo):
   ```bash
   ollama serve
   ```

2. **Ejecuta la aplicación**:
   ```bash
   streamlit run app.py
   ```

3. **Configura las fuentes de datos** en la barra lateral:
   - **FRED**: Ingresa tu API key y selecciona las series económicas a consultar
   - **Indicadores regionales**: Activa la opción e ingresa tu API key de EODHD, selecciona las regiones a monitorear
   - **Noticias públicas**: Activa la opción e ingresa tu API key de NewsAPI, selecciona regiones y categorías de noticias

4. **Haz clic en "Actualizar datos macro"** para cargar la información

5. **Usa el chat** para hacer preguntas sobre el impacto de los datos en el S&P 500

## Arquitectura

### Estructura del proyecto

```
AI-Market-Companion-Hackathon/
├── app.py                          # Interfaz Streamlit principal
├── config/
│   └── data_sources.py            # Configuración de series y categorías
├── core/
│   ├── context_builder.py         # Constructor de contexto para LLM
│   ├── models.py                  # Modelos de datos (SourceResult, TimeSeriesPayload)
│   └── source_registry.py        # Registro de fuentes de datos
├── services/
│   ├── fred_service.py           # Servicio para datos de FRED
│   ├── news_service.py           # Servicio para noticias (NewsAPI/NewsData.io)
│   └── macro_service.py          # Servicio para datos macro (EODHD)
├── processors/
│   ├── sentiment_analyzer.py     # Análisis de sentimiento de noticias
│   └── keyword_filter.py          # Filtro de palabras clave
└── requirements.txt              # Dependencias del proyecto
```

### Componentes principales

- **`app.py`**: Interfaz Streamlit que conecta la barra lateral con los servicios, construye el contexto para el LLM y presenta resultados visuales
- **`config/data_sources.py`**: Catálogo de series económicas de FRED, regiones y categorías de noticias
- **`services/fred_service.py`**: Cliente hacia FRED API, limpieza de datos, creación de resúmenes y snapshots
- **`services/news_service.py`**: Integración con NewsAPI.org y NewsData.io para obtener noticias en tiempo real
- **`services/macro_service.py`**: Integración con EODHD para obtener datos de índices financieros por región
- **`processors/sentiment_analyzer.py`**: Análisis de sentimiento basado en diccionarios de palabras (político, cultural, social)
- **`core/context_builder.py`**: Utilidades para componer el contexto enviado al modelo de lenguaje
- **`core/source_registry.py`**: Registro centralizado de todas las fuentes de datos disponibles

### Flujo de datos

1. **Recolección**: Los servicios (`fred_service`, `news_service`, `macro_service`) obtienen datos de sus respectivas APIs
2. **Procesamiento**: Las noticias pasan por el `sentiment_analyzer` para determinar sentimiento
3. **Contexto**: El `context_builder` consolida toda la información en un formato legible para el LLM
4. **Análisis**: El LLM (Mistral vía Ollama) analiza el contexto y responde preguntas del usuario

## APIs integradas

### FRED (Federal Reserve Economic Data)
- **Uso**: Datos macroeconómicos oficiales de Estados Unidos
- **Series disponibles**: PIB real, tasa de desempleo, índice de precios al consumidor
- **Documentación**: https://fred.stlouisfed.org/docs/api/

### NewsAPI.org
- **Uso**: Noticias en tiempo real por país y categoría
- **Categorías soportadas**: Business, Technology, General (mapeadas a Macro Policy, Trade, Energy, Technology, Geopolitics)
- **Documentación**: https://newsapi.org/docs

### EODHD (End of Day Historical Data)
- **Uso**: Datos de índices financieros y ETFs por región
- **Regiones**: Asia (SPY, FXI), Australia (EWA), Europa (VGK, EWG)
- **Documentación**: https://eodhd.com/docs

### NewsData.io (Alternativa)
- **Uso**: Fuente alternativa de noticias
- **Nota**: Actualmente configurado para usar NewsAPI por defecto, pero se puede cambiar en el código

## Análisis de sentimiento

El sistema incluye un analizador de sentimiento basado en diccionarios de palabras que evalúa tres dimensiones:

- **Político (p)**: Analiza términos relacionados con política, acuerdos, conflictos, estabilidad
- **Cultural (q)**: Evalúa términos relacionados con cultura, educación, innovación, censura
- **Social (s)**: Examina términos relacionados con empleo, bienestar, pobreza, violencia

El sentimiento final se determina combinando estos valores y se clasifica como:
- **Positive**: Cuando la suma de valores es > 0.3
- **Negative**: Cuando la suma de valores es < 0.1
- **Neutral**: En otros casos

## Uso del chat

El chat permite hacer preguntas como:
- "¿Cómo afectan los datos de desempleo al S&P 500?"
- "¿Qué impacto tienen las noticias de Asia en el mercado?"
- "Analiza la tendencia de inflación y su relación con el mercado"
- "¿Qué señales macroeconómicas indican un movimiento alcista?"

El sistema utiliza todo el contexto cargado (datos de FRED, indicadores regionales y noticias) para generar respuestas contextualizadas.

## Próximos pasos sugeridos

- [ ] Incorporar más fuentes de datos (BCE, USDA, EIA, WTO)
- [ ] Agregar almacenamiento de contexto por conversación y trazabilidad de respuestas (LangSmith)
- [ ] Extender las visualizaciones con comparaciones entre series y anotaciones de eventos económicos relevantes
- [ ] Implementar caché de noticias para reducir llamadas a la API
- [ ] Agregar más proveedores de noticias (APITube.io ya está en los scripts)
- [ ] Mejorar el análisis de sentimiento con modelos de ML más avanzados
- [ ] Integrar la tabla de verdad del prototipo para inferencias alzistas/bajistas

## Notas

- Los servicios mock (`mock_macro_service.py` y `mock_news_service.py`) ya no se utilizan pero se mantienen en el proyecto por referencia
- El análisis de sentimiento se basa en el prototipo incluido en `Prototipo código.ipynb`
- Las API keys se pueden configurar tanto en el archivo `.env` como en la interfaz de Streamlit
