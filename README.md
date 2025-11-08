# AI Market Companion

Aplicación construida con Streamlit que combina datos macroeconómicos de la plataforma FRED con un analista conversacional impulsado por LangChain y modelos servidos por Ollama. Permite a los miembros del equipo explorar indicadores macro clave, generar visualizaciones rápidas y obtener un juicio cualitativo sobre el posible impacto en el índice S&P 500.

## Requisitos

- Python 3.10+
- Ollama instalado y ejecutándose en `localhost:11434` con el modelo `mistral` descargado (`ollama pull mistral`)
- Clave de API de [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) para descargar series macroeconómicas

## Instalación

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

1. Inicia Ollama si no está activo.
2. Ejecuta la aplicación:

```bash
streamlit run app.py
```

3. En la barra lateral:
   - Introduce tu clave de FRED.
   - Selecciona las series económicas a consultar (PIB real, tasa de desempleo, inflación).
   - Ajusta el rango temporal y añade contexto manual si lo deseas.

Los datos descargados se muestran como series temporales y se resumen para que el modelo de lenguaje los utilice automáticamente en el análisis.

## Arquitectura rápida

- `app.py`: interfaz Streamlit, descarga de series FRED, generación de contexto y orquestación de la cadena `prompt | llm | parser`.
- `requirements.txt`: dependencias necesarias para ejecutar la demo.

## Próximos pasos sugeridos

- Incorporar las demás fuentes (BCE, News API, USDA, EIA, WTO) señaladas en la documentación del proyecto.
- Agregar almacenamiento de contexto por conversación y trazabilidad de respuestas (LangSmith u otra herramienta).
- Extender las visualizaciones con comparaciones entre series y anotaciones de eventos económicos relevantes.

