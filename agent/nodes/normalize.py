from typing import Any
from agent.state import AgentState
from langchain_core.runnables import RunnableConfig
from indexer.sources.pdf import pdf_ingestor
from indexer.sources.url import url_ingestor
from indexer.cleaning import clean_document
from agent.helper import get_config

def _safe_strip(x: Any) -> str:
    return x.strip() if isinstance(x, str) else ""

def node_normalize_input(
    state: AgentState, config: RunnableConfig | None = None
) -> AgentState:
    """
    Normalize the user input into plain text.

    - text: uses the input as-is
    - pdf: uses pdf_ingestor(...) then clean_document(...)
    - url: uses url_ingestor(...) then clean_document(...)
    """
    cfg = get_config(config)

    if getattr(state, "warnings", None) is None:
        state.warnings = []

    input_kind = _safe_strip(getattr(state, "input_kind", "")).lower()
    input_value = _safe_strip(getattr(state, "input_value", ""))

    if not input_value:
        state.warnings.append("Empty input_value; cannot normalize.")
        state.normalized_text = ""
        return state

    if input_kind == "text":
        state.normalized_text = input_value
        return state
    if input_kind == "pdf":
        source = {"type": "pdf", "path": input_value}
        ingestor = pdf_ingestor
    elif input_kind == "url":
        source = {"type": "url", "url": input_value}
        ingestor = url_ingestor
    else:
        state.warnings.append(f"Unsupported input_kind={input_kind!r}; treating as text.")
        state.normalized_text = input_value
        return state

    doc_id = _safe_strip(getattr(state, "input_id", "")) or "input"
    title = _safe_strip(getattr(state, "input_title", "")) or doc_id
    area = _safe_strip(getattr(state, "area", "")) or "unknown"

    try:
        document = ingestor(
            id=doc_id,
            title=title,
            area=area,
            source=source,
        )

        clean_document(document)

        text = getattr(document, "content", "") or ""
        text = text.strip()

        if not text:
            state.warnings.append(
                f"{input_kind} ingestion produced empty text (id={doc_id})."
            )

        state.normalized_text = text

        return state

    except Exception as exc: 
        state.warnings.append(
            f"Failed to ingest {input_kind} input (id={doc_id}): {exc!r}"
        )
        state.normalized_text = ""
        return state
