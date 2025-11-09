from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

import requests

from config.data_sources import NEWS_CATEGORIES, REGIONAL_MACRO_REGIONS
from core.models import SourceResult
from processors.sentiment_analyzer import analizar_sentimiento_noticia, inferir_tendencia_market

# Funcion para obtener noticias usando NewsAPI.org
def fetch_newsapi_news(
    regions: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
    api_key: Optional[str] = None,
) -> SourceResult:
    """Obtiene noticias usando NewsAPI.org"""
    api_key = api_key or os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        result = SourceResult()
        result.feedback.append(
            ("warning", "API key de NewsAPI no configurada. Usa la variable NEWSAPI_KEY en .env")
        )
        return result

    selected_regions = list(regions) if regions else list(REGIONAL_MACRO_REGIONS.keys())
    selected_categories = list(categories) if categories else NEWS_CATEGORIES
    
    # Mapeo de categorías personalizadas a categorías de NewsAPI
    newsapi_category_map = {
        "Macro Policy": "business",
        "Trade": "business",
        "Energy": "business",
        "Technology": "technology",
        "Geopolitics": "general",
    }
    
    # Mapeo de regiones a códigos de país de NewsAPI
    country_map = {
        "asia": ["cn", "jp", "kr", "in"],
        "australia": ["au"],
        "europe": ["gb", "de", "fr", "it", "es"],
    }
    
    result = SourceResult()
    news_entries: Dict[str, List[Dict[str, str]]] = {}
    
    url = "https://newsapi.org/v2/top-headlines"
    
    for region_id in selected_regions:
        countries = country_map.get(region_id, ["us"])
        region_news = []
        
        for country in countries:
            for category in selected_categories:
                # Mapear categoría personalizada a categoría de NewsAPI
                newsapi_category = newsapi_category_map.get(category, "business")
                params = {
                    "country": country,
                    "category": newsapi_category,
                    "apiKey": api_key,
                    "pageSize": 5,
                }
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    articles = data.get("articles", [])
                    for article in articles:
                        if not article.get("title") or article.get("title") == "[Removed]":
                            continue
                        
                        published_at = article.get("publishedAt", "")
                        try:
                            if published_at:
                                ts = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                            else:
                                ts = datetime.now()
                        except:
                            ts = datetime.now()
                        
                        # Análisis completo de sentimiento e inferencia de tendencia de mercado
                        title_text = article.get("title", "")
                        description_text = article.get("description", "") or ""
                        full_text = f"{title_text} {description_text}"
                        
                        # Análisis básico de sentimiento
                        sentiment_result = analizar_sentimiento_noticia(full_text)
                        sentiment = sentiment_result["sentiment"]
                        
                        # Inferencia completa de tendencia de mercado (lógica del prototipo)
                        tendencia_result = inferir_tendencia_market(full_text, tasa_base=1.0)
                        
                        news_item = {
                            "headline": article.get("title", ""),
                            "category": category,  # Mantener la categoría original
                            "source": article.get("source", {}).get("name", "Unknown"),
                            "sentiment": sentiment,
                            "timestamp": ts.isoformat(),
                            "blurb": article.get("description", "")[:200] or article.get("title", ""),
                            "url": article.get("url", ""),
                            # Datos de inferencia de tendencia de mercado
                            "p": tendencia_result["p"],
                            "q": tendencia_result["q"],
                            "s": tendencia_result["s"],
                            "tendencia": tendencia_result["tendencia"],  # ALZISTA o BAJISTA
                            "es_alzista": tendencia_result["es_alzista"],
                            "tasa": tendencia_result["tasa"],
                            "suma_valores": tendencia_result["suma_valores"],
                        }
                        region_news.append(news_item)
                        
                        # Agregar información completa al contexto para el LLM
                        contexto_linea = (
                            f"{REGIONAL_MACRO_REGIONS.get(region_id, region_id.title())} · {category} · "
                            f"{ts:%Y-%m-%d %H:%M} UTC · {news_item['headline']} ({sentiment}). "
                            f"Análisis: p={tendencia_result['p']:.2f}, q={tendencia_result['q']:.2f}, "
                            f"s={tendencia_result['s']:.2f}. Tendencia: {tendencia_result['tendencia']} "
                            f"(Tasa: {tendencia_result['tasa']:.3f}). {news_item['blurb']}"
                        )
                        result.context_lines.append(contexto_linea)
                        
                except requests.RequestException as e:
                    result.feedback.append(
                        ("warning", f"Error al obtener noticias de {country}/{category}: {str(e)}")
                    )
                    continue
        
        if region_news:
            news_entries[region_id] = region_news
    
    if news_entries:
        result.extra["news"] = news_entries
    
    if not result.context_lines:
        result.feedback.append(
            ("info", "No se encontraron noticias para los filtros seleccionados.")
        )
    
    return result

# Funcion para obtener noticias usando NewsData.io
def fetch_newsdata_news(
    regions: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
    api_key: Optional[str] = None,
) -> SourceResult:
    """Obtiene noticias usando NewsData.io"""
    api_key = api_key or os.getenv("NEWSDATA_KEY", "")
    if not api_key:
        result = SourceResult()
        result.feedback.append(
            ("warning", "API key de NewsData.io no configurada. Usa la variable NEWSDATA_KEY en .env")
        )
        return result

    selected_regions = list(regions) if regions else list(REGIONAL_MACRO_REGIONS.keys())
    selected_categories = list(categories) if categories else NEWS_CATEGORIES
    
    # Mapeo de categorías
    category_map = {
        "Macro Policy": "business",
        "Trade": "business",
        "Energy": "science",
        "Technology": "technology",
        "Geopolitics": "politics",
    }
    
    result = SourceResult()
    news_entries: Dict[str, List[Dict[str, str]]] = {}
    
    url = "https://newsdata.io/api/1/news"
    
    for region_id in selected_regions:
        region_news = []
        
        # Mapeo de regiones a códigos de país
        country_map = {
            "asia": "us",  # NewsData usa códigos diferentes, ajustar según necesidad
            "australia": "au",
            "europe": "gb",
        }
        country = country_map.get(region_id, "us")
        
        for category in selected_categories:
            newsdata_category = category_map.get(category, "business")
            
            params = {
                "apikey": api_key,
                "country": country,
                "category": newsdata_category,
                "language": "en",
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                articles = data.get("results", [])
                for article in articles[:5]:  # Limitar a 5 por categoría
                    if not article.get("title"):
                        continue
                    
                    published_at = article.get("pubDate", "")
                    try:
                        if published_at:
                            ts = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        else:
                            ts = datetime.now()
                    except:
                        ts = datetime.now()
                    
                    # Análisis completo de sentimiento e inferencia de tendencia de mercado
                    title_text = article.get("title", "")
                    description_text = article.get("description", "") or ""
                    full_text = f"{title_text} {description_text}"
                    
                    # Análisis básico de sentimiento
                    sentiment_result = analizar_sentimiento_noticia(full_text)
                    sentiment = sentiment_result["sentiment"]
                    
                    # Inferencia completa de tendencia de mercado (lógica del prototipo)
                    tendencia_result = inferir_tendencia_market(full_text, tasa_base=1.0)
                    
                    news_item = {
                        "headline": article.get("title", ""),
                        "category": category,
                        "source": article.get("source_id", "Unknown"),
                        "sentiment": sentiment,
                        "timestamp": ts.isoformat(),
                        "blurb": article.get("description", "")[:200] or article.get("title", ""),
                        "url": article.get("link", ""),
                        # Datos de inferencia de tendencia de mercado
                        "p": tendencia_result["p"],
                        "q": tendencia_result["q"],
                        "s": tendencia_result["s"],
                        "tendencia": tendencia_result["tendencia"],  # ALZISTA o BAJISTA
                        "es_alzista": tendencia_result["es_alzista"],
                        "tasa": tendencia_result["tasa"],
                        "suma_valores": tendencia_result["suma_valores"],
                    }
                    region_news.append(news_item)
                    
                    # Agregar información completa al contexto para el LLM
                    contexto_linea = (
                        f"{REGIONAL_MACRO_REGIONS.get(region_id, region_id.title())} · {category} · "
                        f"{ts:%Y-%m-%d %H:%M} UTC · {news_item['headline']} ({sentiment}). "
                        f"Análisis: p={tendencia_result['p']:.2f}, q={tendencia_result['q']:.2f}, "
                        f"s={tendencia_result['s']:.2f}. Tendencia: {tendencia_result['tendencia']} "
                        f"(Tasa: {tendencia_result['tasa']:.3f}). {news_item['blurb']}"
                    )
                    result.context_lines.append(contexto_linea)
                    
            except requests.RequestException as e:
                result.feedback.append(
                    ("warning", f"Error al obtener noticias de NewsData.io para {region_id}/{category}: {str(e)}")
                )
                continue
        
        if region_news:
            news_entries[region_id] = region_news
    
    if news_entries:
        result.extra["news"] = news_entries
    
    if not result.context_lines:
        result.feedback.append(
            ("info", "No se encontraron noticias para los filtros seleccionados.")
        )
    
    return result


# Funcion para obtener noticias usando NewsAPI.org o NewsData.io
def fetch_news(
    regions: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
    api_key: Optional[str] = None,
    provider: str = "newsapi",
) -> SourceResult:
    """
    Función principal para obtener noticias.
    Por defecto usa NewsAPI, pero puede cambiar a NewsData.io
    """
    if provider == "newsdata":
        return fetch_newsdata_news(regions, categories, api_key)
    else:
        return fetch_newsapi_news(regions, categories, api_key)

