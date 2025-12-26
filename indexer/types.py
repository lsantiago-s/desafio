from pydantic import BaseModel
from typing import Literal, Optional, Dict, List, Any

class Document(BaseModel):
    """ Document to be indexed. """
    doc_id: str
    title: str
    area: str
    source_type: Literal["pdf", "url", "text"]
    content: str
    source_uri: str # path if pdf or text, url if url
    page_map: List[Dict[str, Any]]
    ingest_warnings: List[str] = []
    ingest_stats: Dict[str, Any] = {}

class Chunk(BaseModel):
    """ Chunk of text from a document. """
    chunk_id: str  # f"{doc_id}::p{page_start}-{page_end}::c{chunk_index}"
    doc_id: str
    area: str
    text: str
    source_uri: str
    page_start: Optional[int]
    page_end: Optional[int]  # if url/text source
    char_start: int
    char_end: int
    token_count: int