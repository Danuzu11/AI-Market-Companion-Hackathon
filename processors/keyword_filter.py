# Aqui sacamos la función para filtrar las líneas por palabras clave
from typing import Iterable, List, Sequence


# Función para filtrar las líneas por palabras clave
def filter_lines_by_keywords(
    lines: Iterable[str],
    keywords: Sequence[str],
) -> List[str]:
    """
    Función para filtrar las líneas por palabras clave.
    
    Parámetros:
        - lines: Iterable con las líneas a inspeccionar.
        - keywords: Lista de palabras clave en minúsculas para preservar.
    
    Retorna:
        - Lista de líneas que contienen al menos una palabra clave. Si no hay palabras clave, se devuelven las líneas originales.
    """
    # Convertir las palabras clave a minúsculas
    normalized = [kw.lower() for kw in keywords if kw]

    # Si no hay palabras clave, devolver las líneas originales
    if not normalized:
        return list(lines)

    # Inicializar la lista de líneas filtradas
    filtered = []
    # Recorrer las líneas
    for line in lines:
        # Convertir la línea a minúsculas
        text = line.lower()
        # Si la línea contiene alguna de las palabras clave, añadirla a la lista de líneas filtradas
        if any(keyword in text for keyword in normalized):
            filtered.append(line)
    return filtered

