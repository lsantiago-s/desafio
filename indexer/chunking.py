# Receives Document and splits into list[Chunk], source agnostic
from indexer.types import Chunk
from indexer.types import Document

def chunk_document(document: Document, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Parses and chunks the given Document.

    Args:
        document (Document): The document to be chunked.
        chunk_size (int): The size of each chunk.
        chunk_overlap (int): The overlap between chunks.

    Returns:
        list[Chunk]: A list of chunks created from the document.
    """
    chunks = []
    content = document.content
    doc_id = document.doc_id
    area = document.area
    source_type = document.source_type
    page_map = document.page_map

    char_start = 0
    chunk_index = 0

    while char_start < len(content):
        char_end = min(char_start + chunk_size, len(content))
        chunk_text = content[char_start:char_end]

        page_start = None
        page_end = None
        accumulated_chars = 0
        for page in page_map:
            page_length = len(page["text"])
            if accumulated_chars <= char_start < accumulated_chars + page_length:
                page_start = page["page_idx"]
            if accumulated_chars < char_end <= accumulated_chars + page_length:
                page_end = page["page_idx"]
            accumulated_chars += page_length + 2  # +2 for the "\n\n" added during extraction

        chunk_id = f"{doc_id}::p{page_start}-{page_end}::c{chunk_index}"

        chunk = Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            area=area,
            text=chunk_text,
            page_start=page_start,
            page_end=page_end,
            source_uri=document.source_uri,
            char_start=char_start,
            char_end=char_end,
            token_count=len(chunk_text.split())
        )
        chunks.append(chunk)

        chunk_index += 1
        char_start += chunk_size - chunk_overlap

    return chunks