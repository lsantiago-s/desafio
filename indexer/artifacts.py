# Save processed/#.jsonl, stats, manifest, etc. to processed_dir
import json
from typing import List
from indexer.types import Chunk

def write_chunks_jsonl(doc_id: str, chunks: List[Chunk], processed_dir: str):
    jsonl_path = f"{processed_dir}/{doc_id}_chunks.jsonl"
    with open(jsonl_path, 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk.model_dump()) + '\n')

def append_document_stats(stats: dict, document, chunks: List[Chunk], warnings: List[str]):
    stats[document.doc_id] = {
        "n_chunks": len(chunks),
        "ingest_warnings": document.ingest_warnings,
        "ingest_stats": document.ingest_stats
    }

def append_manifest_json(manifest: dict, embedding_config: dict, chunking_config: dict, vector_store_config: dict):
    """Record embedding config (through embedder.inf()), chunking config, vector store config and metadata."""
    manifest["embedding_config"] = embedding_config
    manifest["chunking_config"] = chunking_config
    manifest["vector_store_config"] = vector_store_config

def write_stats_json(stats: dict, processed_dir: str):
    stats_path = f"{processed_dir}/stats.json"
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)

def write_manifest_json(manifest: dict, processed_dir: str):
    manifest_path = f"{processed_dir}/manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)