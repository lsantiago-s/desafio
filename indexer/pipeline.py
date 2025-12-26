import os
import json
from indexer.sources.pdf import pdf_ingestor
from indexer.sources.url import url_ingestor
from indexer.sources.text import text_ingestor
from indexer.artifacts import write_chunks_jsonl, append_document_stats, append_manifest_json, write_stats_json, write_manifest_json
from indexer.chunking import chunk_document
from indexer.cleaning import clean_document
from indexer.embeddings import EmbeddingConfig, Embedder
from indexer.store.chroma_store import initialize_chroma_collection, upsert_chunks

def run_indexing_pipeline(
    metadata_path: str,
    chroma_dir: str,
    processed_dir: str,
    collection_name: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_config: dict,
    reset: bool,
):
    
    # Load metadata from metadata_path
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    # Load embedding model
    embedder = Embedder(EmbeddingConfig(**embedding_config))

    # Create ChromaDB collection at chroma_dir under collection_name
    os.makedirs(chroma_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    chroma_collection = initialize_chroma_collection(chroma_dir, collection_name, reset=reset)

    # Initialize stats and manifest dict
    stats = {}
    manifest = {}
    
    # For each entry in metadata, determine source type (e.g., PDF, URL)

    for entry in metadata:
        try:
            source_type = entry.get("source", {}).get("type")
            if source_type == "pdf":
                document = pdf_ingestor(
                    id=entry["id"],
                    title=entry["title"],
                    area=entry["area"],
                    source=entry["source"]
                )
            elif source_type == "url":
                document = url_ingestor(
                    id=entry["id"],
                    title=entry["title"],
                    area=entry["area"],
                    source=entry["source"]
                )
            elif source_type == "text":
                document = text_ingestor(
                    id=entry["id"],
                    title=entry["title"],
                    area=entry["area"],
                    source=entry["source"]
                )
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            # Clean the Document content
            clean_document(document)

            # Chunk the Document into smaller Chunks using chunk_size and chunk_overlap
            chunks = chunk_document(document, chunk_size, chunk_overlap)
            if chunks == []:
                document.ingest_warnings.append("No chunks were created from the document content.")
            warnings = document.ingest_warnings

            # Store the Chunks into ChromaDB located at chroma_dir under collection_name
            write_chunks_jsonl(document.doc_id, chunks, processed_dir)

            # Save jsonl files to processed_dir for record-keepings
            upsert_chunks(chroma_collection, chunks, embedder)
        
            # Save stat + manifest files to processed_dir
            append_document_stats(stats, document, chunks, warnings)
        except Exception as e:
            print(f"Error processing entry {entry.get('id', 'unknown')}: {e}")
            continue

    append_manifest_json(
        manifest=manifest,
        embedding_config=embedder.info(),
        chunking_config={
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        },
        vector_store_config={
            "type": "chroma",
            "chroma_dir": chroma_dir,
            "collection_name": collection_name,
            "reset": reset
        }
    )
    write_stats_json(stats, processed_dir)
    write_manifest_json(manifest, processed_dir)