from typing import Dict, Tuple, Optional
import pandas as pd
import os


# Diccionario de palabras para análisis de sentimiento
SENTIMENT_DICTIONARY = {
    "politico": {
        "positivo": ["acuerdo", "estabilidad", "cooperación", "democracia", "paz", "diplomacia", "alianza"],
        "negativo": ["crisis", "corrupción", "protesta", "conflicto", "guerra", "tensión", "sanción"]
    },
    "cultural": {
        "positivo": ["arte", "innovación", "educación", "tolerancia", "cultura", "creatividad", "diversidad"],
        "negativo": ["censura", "discriminación", "abandono", "crítica", "represión", "intolerancia"]
    },
    "social": {
        "positivo": ["empleo", "igualdad", "salud", "bienestar", "prosperidad", "crecimiento", "desarrollo"],
        "negativo": ["pobreza", "violencia", "inseguridad", "desempleo", "recesión", "crisis", "conflicto"]
    }
}

# Tabla de verdad para inferencia alzista/bajista
# Estructura: p, q, s, escenario1, escenario2, ..., escenarioN
# Donde 1 = alzista, 0 = bajista
TRUTH_TABLE = pd.DataFrame([
    # p, q, s, escenario1, escenario2, escenario3, escenario4
    [0, 0, 0, 0, 0, 0, 0],  # Todo negativo -> Bajista
    [0, 0, 1, 0, 0, 0, 1],  # Solo social positivo -> Mixto (principalmente bajista)
    [0, 1, 0, 0, 0, 1, 0],  # Solo cultural positivo -> Mixto
    [0, 1, 1, 0, 1, 1, 1],  # Cultural y social positivo -> Alzista
    [1, 0, 0, 0, 1, 0, 0],  # Solo político positivo -> Mixto
    [1, 0, 1, 1, 0, 1, 1],  # Político y social positivo -> Alzista
    [1, 1, 0, 1, 1, 0, 1],  # Político y cultural positivo -> Alzista
    [1, 1, 1, 1, 1, 1, 1],  # Todo positivo -> Alzista
], columns=['p', 'q', 's', 'escenario1', 'escenario2', 'escenario3', 'escenario4'])


def calcular_valores_sentimiento(texto: str, dic: Dict = None) -> Tuple[float, float, float]:
    """
    Calcula valores numéricos de p (político), q (cultural), s (social)
    basado en el análisis de sentimiento del texto.
    
    Returns:
        Tuple[float, float, float]: Valores de p, q, s normalizados entre 0 y 1
    """
    if dic is None:
        dic = SENTIMENT_DICTIONARY
    
    texto = texto.lower()
    
    def contar(sentimiento: str) -> Tuple[int, int]:
        """Cuenta palabras positivas y negativas para un tema"""
        positivas = sum(1 for palabra in dic[sentimiento]["positivo"] if palabra in texto)
        negativas = sum(1 for palabra in dic[sentimiento]["negativo"] if palabra in texto)
        return positivas, negativas
    
    resultados = {}
    for tema in dic.keys():
        pos, neg = contar(tema)
        total = pos + neg if (pos + neg) > 0 else 1
        score = (pos - neg) / total  # entre -1 y +1
        resultados[tema] = max(0, score)  # recorta negativos a 0
    
    return resultados["politico"], resultados["cultural"], resultados["social"]


def analizar_sentimiento_noticia(texto: str) -> Dict[str, any]:
    """
    Analiza el sentimiento de una noticia y retorna un diccionario con los resultados.
    
    Returns:
        Dict con keys: 'sentiment' (positive/negative/neutral), 'p', 'q', 's', 'score'
    """
    p_val, q_val, s_val = calcular_valores_sentimiento(texto)
    suma_valores = p_val + q_val + s_val
    
    # Determinar sentimiento general
    if suma_valores > 0.3:
        sentiment = "positive"
    elif suma_valores < 0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    return {
        "sentiment": sentiment,
        "p": p_val,
        "q": q_val,
        "s": s_val,
        "score": suma_valores,
    }


def inferir_tendencia_market(
    texto: str,
    tabla_verdad: Optional[pd.DataFrame] = None,
    tasa_base: float = 1.0
) -> Dict[str, any]:
    """
    Implementa la lógica completa del prototipo:
    1. Calcula valores p, q, s del texto
    2. Busca en la tabla de verdad
    3. Determina si es alzista o bajista
    4. Calcula la tasa
    
    Args:
        texto: Texto de noticias a analizar
        tabla_verdad: DataFrame con la tabla de verdad (opcional, usa la predeterminada si no se proporciona)
        tasa_base: Tasa base del S&P500 normalizada (default: 1.0)
    
    Returns:
        Dict con keys: 'p', 'q', 's', 'es_alzista', 'tasa', 'suma_valores'
    """
    if tabla_verdad is None:
        tabla_verdad = TRUTH_TABLE
    
    # Calcular valores p, q, s
    p_val, q_val, s_val = calcular_valores_sentimiento(texto)
    
    # Convertir a binario (0 o 1) para buscar en la tabla
    p_bin = int(p_val > 0)
    q_bin = int(q_val > 0)
    s_bin = int(s_val > 0)
    
    # Buscar la fila correspondiente en la tabla de verdad
    tabla_match = tabla_verdad[
        (tabla_verdad['p'] == p_bin) &
        (tabla_verdad['q'] == q_bin) &
        (tabla_verdad['s'] == s_bin)
    ]
    
    if tabla_match.empty:
        # Si no hay coincidencia, usar lógica por defecto
        es_alzista = (p_val + q_val + s_val) > 0.5
    else:
        # Si hay varias filas, tomar la primera
        fila = tabla_match.iloc[0]
        # Determinar si la inferencia es alzista o bajista
        # (la columna con valor 1 indica escenario alzista)
        # Ignoramos las primeras 3 columnas (p, q, s)
        columnas_escenarios = [col for col in fila.index if col not in ['p', 'q', 's']]
        es_alzista = any(fila[col] == 1 for col in columnas_escenarios)
    
    # Calcular la tasa
    suma_valores = p_val + q_val + s_val
    
    if es_alzista:
        tasa = tasa_base * (1 + suma_valores)
    else:
        tasa = tasa_base * (1 - suma_valores)
    
    return {
        "p": p_val,
        "q": q_val,
        "s": s_val,
        "p_bin": p_bin,
        "q_bin": q_bin,
        "s_bin": s_bin,
        "es_alzista": es_alzista,
        "tasa": tasa,
        "suma_valores": suma_valores,
        "tendencia": "ALZISTA" if es_alzista else "BAJISTA",
    }


def cargar_tabla_verdad_desde_excel(ruta_archivo: str) -> Optional[pd.DataFrame]:
    """
    Carga la tabla de verdad desde un archivo Excel.
    
    Args:
        ruta_archivo: Ruta al archivo Excel con la tabla de verdad
    
    Returns:
        DataFrame con la tabla de verdad o None si hay error
    """
    try:
        if os.path.exists(ruta_archivo):
            tabla = pd.read_excel(ruta_archivo)
            return tabla
        else:
            return None
    except Exception as e:
        print(f"Error al cargar tabla de verdad desde Excel: {e}")
        return None

