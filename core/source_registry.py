from dataclasses import dataclass
from typing import Callable, Dict, List

from services import fred_service, macro_service, news_service


@dataclass(frozen=True)
class SourceConfig:
    id: str
    label: str
    fetcher: Callable
    requires_api_key: bool = False


SOURCE_REGISTRY: Dict[str, SourceConfig] = {
    "fred": SourceConfig(
        id="fred",
        label="FRED",
        fetcher=fred_service.collect_fred_data,
        requires_api_key=True,
    ),
    "macro_regional": SourceConfig(
        id="macro_regional",
        label="Indicadores regionales",
        fetcher=macro_service.fetch_regional_macro,
        requires_api_key=True,
    ),
    "news_public": SourceConfig(
        id="news_public",
        label="Noticias públicas",
        fetcher=news_service.fetch_news,
        requires_api_key=True,
    ),
}


def list_sources() -> List[SourceConfig]:
    return list(SOURCE_REGISTRY.values())


def get_source_config(source_id: str) -> SourceConfig:
    return SOURCE_REGISTRY[source_id]

