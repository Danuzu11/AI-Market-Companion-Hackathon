# AI Market Companion

Aplicación construida con Streamlit que combina datos macroeconómicos de la plataforma FRED con un analista conversacional impulsado por Google Gemini. Permite a los miembros del equipo explorar indicadores macro clave, generar visualizaciones rápidas y obtener un juicio cualitativo sobre el posible impacto en el índice S&P 500.

## Requisitos

- Python 3.10+
- Conda o Python con venv
- Clave de API de [Google Gemini](https://aistudio.google.com/app/apikey) para el análisis con IA (gratuita)
- Clave de API de [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) para descargar series macroeconómicas
- Clave de API de [NewsAPI](https://newsapi.org/) para obtener noticias (gratuita)

## Instalación

### Opción 1: Usando Conda (Recomendado)

```bash
# Crear ambiente conda
conda create -n ai-market-companion python=3.10 -y

# Activar ambiente
conda activate ai-market-companion

# Instalar dependencias
pip install -r requirements.txt
```

### Opción 2: Usando venv

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración de API Keys

La aplicación puede cargar las API keys desde un archivo `.env` o ingresarlas manualmente en el sidebar.

### Opción 1: Usar archivo .env (Recomendado)

1. Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env
   ```

2. Edita el archivo `.env` y agrega tus API keys:
   ```env
   FRED_API_KEY=tu_fred_api_key_aqui
   NEWS_API_KEY=tu_news_api_key_aqui
   GEMINI_API_KEY=tu_gemini_api_key_aqui
   ```

3. **Importante**: El archivo `.env` está en `.gitignore` y no se subirá al repositorio. Mantén tus API keys seguras.

### Opción 2: Ingresar manualmente en el sidebar

También puedes ingresar las API keys directamente en el panel lateral de la aplicación. Las keys ingresadas manualmente tienen prioridad sobre las del archivo `.env`.

## Ejecución

1. **Obtén tu API key de Google Gemini:**
   - Visita https://aistudio.google.com/app/apikey
   - Crea una nueva API key (gratuita)
   - Copia la clave para usarla en la aplicación

2. **Activa el ambiente conda (si usaste conda):**
   ```bash
   conda activate ai-market-companion
   ```

3. **Ejecuta la aplicación:**
   ```bash
   streamlit run app.py
   ```
   
   O usa los scripts proporcionados:
   - Windows: Doble clic en `run_app.bat`
   - PowerShell: `.\run_app.ps1`

3. En la barra lateral:
   - Introduce tu clave de API de FRED.
   - Introduce tu clave de API de NewsAPI.
   - Introduce tu clave de API de Google Gemini.
   - Selecciona las series económicas a consultar (PIB real, tasa de desempleo, inflación, tipos de cambio).
   - Ajusta el rango temporal (por defecto: última semana).
   - Haz clic en "🔄 Actualizar datos y analizar".

El sistema automáticamente:
- Descarga datos económicos de FRED
- Obtiene noticias relevantes de Asia, Australia y Europa
- Analiza el impacto potencial en el S&P 500 (POSITIVO/NEGATIVO/NEUTRAL)

## Arquitectura rápida

- `app.py`: interfaz Streamlit, descarga de series FRED, generación de contexto e integración directa con la API de Google Gemini.
- `requirements.txt`: dependencias necesarias para ejecutar la demo (incluye `google-generativeai` para interactuar directamente con Gemini).

## Próximos pasos sugeridos

- Incorporar las demás fuentes (BCE, News API, USDA, EIA, WTO) señaladas en la documentación del proyecto.
- Agregar almacenamiento de contexto por conversación y trazabilidad de respuestas (LangSmith u otra herramienta).
- Extender las visualizaciones con comparaciones entre series y anotaciones de eventos económicos relevantes.

