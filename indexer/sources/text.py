from indexer.types import Document
from typing import Dict, Literal

def text_ingestor(id: str, title: str, area: str, source: Dict[Literal["type", "content"], str]) -> Document:

    if source["type"] != "text":
        raise ValueError(f"Source type must be 'text', got {source['type']} instead.")

    ingest_warnings = []
    ingest_stats = {}

    extracted_text = source["content"]

    ingest_stats["n_chars"] = len(extracted_text)

    if len(extracted_text.strip()) == 0:
        ingest_warnings.append("Text content is empty.")

    document = Document(
        doc_id=id,
        title=title,
        area=area,
        source_type="text",
        source_uri=f"inline:{id}",
        content=extracted_text,
        page_map=[],
        ingest_warnings=ingest_warnings,
        ingest_stats=ingest_stats
    )

    return document