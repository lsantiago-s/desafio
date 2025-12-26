# Receives chunks and indexes them into ChromaDB

import chromadb
from chromadb.config import Settings
from typing import List
from indexer.types import Chunk

def initialize_chroma_collection(chroma_dir: str, collection_name: str, reset: bool):
    client = chromadb.PersistentClient(path=chroma_dir, settings=Settings(anonymized_telemetry=False))
    if reset:
        client.delete_collection(name=collection_name)
    collection = client.get_or_create_collection(name=collection_name)
    return collection

def upsert_chunks(
    chroma_collection,
    chunks: List[Chunk],
    embedder,
):
    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        texts = [chunk.text for chunk in batch_chunks]
        embeddings = embedder.embed_texts(texts)
        ids = [chunk.chunk_id for chunk in batch_chunks]
        metadatas = [
            {
            key: value
            for key, value in {
                "doc_id": chunk.doc_id,
                "area": chunk.area,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "source_uri": chunk.source_uri,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "token_count": chunk.token_count,
            }.items()
            if value is not None
            }
            for chunk in batch_chunks
        ]
        chroma_collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )