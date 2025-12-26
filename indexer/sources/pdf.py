# Ler pdf, devolver Document com page_map
from indexer.types import Document
from typing import Dict, Literal
from io import BytesIO
from pypdf import PdfReader
import pymupdf
import re

_NONSPACE_RE = re.compile(r"\S")

def extract_text_from_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def pdf_ingestor(id: str, title: str, area: str, source: Dict[Literal["type", "path"], str]) -> Document:

    # 1) preflight: check if file exists, is pdf, size limits, etc.
    try:
        raw_doc = pymupdf.open(source["path"])
    except FileNotFoundError:
        raise ValueError(f"PDF file not found at {source['path']}")
    
    if source["type"] != "pdf":
        raise ValueError(f"File at {source['path']} is not a PDF.")
    
    if raw_doc.page_count == 0:
        raise ValueError(f"PDF at {source['path']} has zero pages.")

    if raw_doc.is_encrypted:
        raise ValueError(f"PDF at {source['path']} is encrypted and cannot be processed.")

    ingest_warnings = []
    ingest_stats = {}

    # 2) read pdf, extract text per page
    page_map = []
    i = 1
    for page in raw_doc:
        page_content = page.get_text()
        assert isinstance(page_content, str)
        nonspace = len(_NONSPACE_RE.findall(page_content))
        page_number = i
        page_map.append({"page_idx": page_number, "text": page_content, "char_count": len(page_content), "nonspace_char_count": nonspace})
        i += 1
    extracted_text = "\n\n".join([p["text"] for p in page_map])

    # 3) Quality checks: empty pdf, scanned pdf (no text), etc.
    ingest_stats["n_pages"] = raw_doc.page_count
    ingest_stats["n_chars"] = len(extracted_text)
    ingest_stats["n_extracted_pages"] = len(page_map)
    # ingest_stats["chars_per_page"] = {k: len(v) for k, v in page_map.items()}
    ingest_stats["non_ascii_ratio"] = sum(1 for c in extracted_text if ord(c) > 127) / max(1, len(extracted_text))
    
    if len(extracted_text.strip()) == 0:
        ingest_warnings.append("Low text content in PDF.")
    if len(page_map) == 0:
        ingest_warnings.append("PDF has no extractable text.")
    if all(len(p["text"].strip()) == 0 for p in page_map):
        ingest_warnings.append("PDF appears to be scanned or image-only, no text extracted.")
    if not extracted_text or sum(p["nonspace_char_count"] for p in page_map) < 200:
        ingest_warnings.append("PDF extraction produced very little text content.")
    # 4) Fallback strategies: OCR?
    if "Low text content in PDF." in ingest_warnings or "PDF appears to be scanned or image-only, no text extracted." in ingest_warnings:
        ingest_warnings.append("Consider using OCR to extract text from scanned PDFs.")
    
    # 5) build document
    document = Document(
        doc_id=id,
        title=title,
        area=area,
        source_type="pdf",
        source_uri=source["path"],
        content=extracted_text,
        page_map=page_map,
        ingest_warnings=ingest_warnings,
        ingest_stats=ingest_stats
    )

    return document