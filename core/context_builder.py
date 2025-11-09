from typing import Dict, Iterable, List


def compose_context(
    source_context: Dict[str, Iterable[str]],
    include_headers: bool = True,
) -> str:
    """
    Combine context fragments from different data sources into a single prompt-ready string.

    Parameters
    ----------
    source_context:
        Mapping {source_name: iterable of lines}. Each iterable will be joined
        with newlines and optionally preceded by a header.
    include_headers:
        If True, adds a header with the source name before its content. The
        source name is capitalized for readability.
    """
    chunks: List[str] = []
    for source_name, lines in source_context.items():
        lines = list(lines)
        if not lines:
            continue
        if include_headers:
            chunks.append(f"Fuente: {source_name.upper()}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)

