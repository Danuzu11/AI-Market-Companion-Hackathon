from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from config.data_sources import NEWS_CATEGORIES, REGIONAL_MACRO_REGIONS
from core.models import SourceResult


SYNTHETIC_NEWS_DATA: Dict[str, List[Dict[str, str]]] = {
    "asia": [
        {
            "headline": "China anuncia paquete de infraestructura verde por $120B",
            "category": "Macro Policy",
            "source": "Xinhua",
            "sentiment": "positive",
            "timestamp": "2025-10-02T08:30:00Z",
            "blurb": "La inversión apunta a estabilizar el crecimiento y reforzar la transición energética.",
        },
        {
            "headline": "Tensiones comerciales Japón-Corea reavivan controles de exportación",
            "category": "Trade",
            "source": "Nikkei Asia",
            "sentiment": "negative",
            "timestamp": "2025-10-03T05:10:00Z",
            "blurb": "Las restricciones podrían afectar cadenas de suministro de semiconductores.",
        },
    ],
    "australia": [
        {
            "headline": "Gobierno australiano presenta plan de subsidios para hidrógeno",
            "category": "Energy",
            "source": "ABC",
            "sentiment": "positive",
            "timestamp": "2025-10-01T21:45:00Z",
            "blurb": "Se busca atraer inversión asiática y consolidar liderazgo en energías limpias.",
        },
        {
            "headline": "Mineras australianas alertan caída en demanda de mineral de hierro",
            "category": "Trade",
            "source": "Financial Review",
            "sentiment": "negative",
            "timestamp": "2025-10-04T02:00:00Z",
            "blurb": "La desaceleración china presiona precios y envíos previstos para 2026.",
        },
    ],
    "europe": [
        {
            "headline": "BCE adelanta que podría reducir balance más rápido",
            "category": "Macro Policy",
            "source": "Reuters",
            "sentiment": "negative",
            "timestamp": "2025-10-02T11:15:00Z",
            "blurb": "El mercado descuenta condiciones financieras más estrictas a inicios de 2026.",
        },
        {
            "headline": "Alemania impulsa paquete fiscal para reactivar inversión industrial",
            "category": "Macro Policy",
            "source": "Handelsblatt",
            "sentiment": "positive",
            "timestamp": "2025-10-03T09:22:00Z",
            "blurb": "Incluye incentivos para producción de baterías y tecnologías limpias.",
        },
    ],
}


def fetch_mock_news(
    regions: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
) -> SourceResult:
    selected_regions = list(regions) if regions else list(SYNTHETIC_NEWS_DATA.keys())
    selected_categories = {cat for cat in (categories or NEWS_CATEGORIES)}
    result = SourceResult()
    news_entries: Dict[str, List[Dict[str, str]]] = {}

    for region_id in selected_regions:
        entries = SYNTHETIC_NEWS_DATA.get(region_id, [])
        filtered = [
            item for item in entries if item["category"] in selected_categories
        ]
        if not filtered:
            continue

        news_entries[region_id] = filtered
        label = REGIONAL_MACRO_REGIONS.get(region_id, region_id.title())
        for item in filtered:
            ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            result.context_lines.append(
                f"{label} · {item['category']} · {ts:%Y-%m-%d %H:%M} UTC · {item['headline']} ({item['sentiment']}). {item['blurb']}"
            )

    if news_entries:
        result.extra["news"] = news_entries

    if not result.context_lines:
        result.feedback.append(
            (
                "info",
                "No se encontraron noticias ficticias para los filtros seleccionados.",
            )
        )

    return result

