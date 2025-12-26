import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from indexer.embeddings import EmbeddingConfig, Embedder
import chromadb

@dataclass(frozen=True)
class DocMeta:
    title: str
    area: str
    source_uri: str | None = None

@dataclass
class AppState:
    collection: Any
    doc_meta: dict[str, DocMeta]
    embed_query: Callable[[str], list[float]]

def load_doc_meta(metadata_path: Path) -> dict[str, DocMeta]:
    if not metadata_path.exists():
        return {}
    
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    meta: dict[str, DocMeta] = {}

    if isinstance(raw, dict):
        for doc_id, info in raw.items():
            meta[doc_id] = DocMeta(
                title=info.get("title", "Untitled"),
                area=info.get("area", "General"),
                source_uri=info.get("source_uri")
            )
    elif isinstance(raw, list):
        for entry in raw:
            doc_id = entry.get("doc_id")
            if doc_id:
                meta[doc_id] = DocMeta(
                    title=entry.get("title", "Untitled"),
                    area=entry.get("area", "General"),
                    source_uri=entry.get("source_uri")
                )
    return meta

def init_state(chroma_dir: Path, collection_name: str, metadata_path: Path, manifest_path: Path) -> AppState:
    client = chromadb.PersistentClient(chroma_dir)
    collection = client.get_collection(collection_name, embedding_function=None)
    doc_meta = load_doc_meta(metadata_path)
    embedder = Embedder.from_manifest(manifest_path)
    f_query = lambda text: embedder.embed_texts([text])[0]
    return AppState(collection=collection, doc_meta=doc_meta, embed_query=f_query)