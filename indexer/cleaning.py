import re
from typing import Protocol

class HasContentAndWarnings(Protocol):
    content: str
    ingest_warnings: list[str]

_WS_RE = re.compile(r"[ \t\f\v]+")
_MANY_NEWLINES_RE = re.compile(r"\n{3,}")

def clean_document(document: HasContentAndWarnings) -> HasContentAndWarnings:
    """
    Cleans document.content in-place and appends warnings to document.ingest_warnings.

    Actions performed:
    - Normalize newlines to '\n'
    - Remove null bytes and other control chars that break JSON/DB
    - Collapse excessive whitespace while preserving paragraph breaks
    - Ensure deterministic output
    """
    text = document.content or ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if "\x00" in text:
        text = text.replace("\x00", "")
        document.ingest_warnings.append("Null bytes removed during cleaning.")

    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MANY_NEWLINES_RE.sub("\n\n", text)
    text = text.strip()

    document.content = text

    if not document.content:
        document.ingest_warnings.append("Document content is empty after cleaning.")

    return document
