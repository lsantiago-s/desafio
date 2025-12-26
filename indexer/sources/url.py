from indexer.types import Document
from typing import Dict, Literal, Final
import re
import requests
from bs4 import BeautifulSoup
from readability import Document as ReadabilityDoc
from indexer.sources.pdf import extract_text_from_pdf_bytes  # implement once

_BOILERPLATE_PATTERNS: Final[list[str]] = [
    r"cookie",
    r"consent",
    r"privacy",
    r"terms",
    r"subscribe",
    r"sign in",
    r"newsletter",
]


def _looks_like_pdf(content_type: str | None, url: str) -> bool:
    ct = (content_type or "").lower()
    if "application/pdf" in ct:
        return True
    return url.lower().split("?")[0].endswith(".pdf")


def _clean_whitespace(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _extract_text_from_html(html: str) -> str:
    assert isinstance(_BOILERPLATE_PATTERNS, list), type(_BOILERPLATE_PATTERNS)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article")
    root = main if main is not None else soup.body or soup

    for el in root.find_all(True):
        cls_id = " ".join(
            [*(el.get("class") or []), (el.get("id") or "")]
        ).lower()
        if any(pat in cls_id for pat in ["nav", "menu", "footer", "header", "sidebar"]):
            el.decompose()

    text = root.get_text(separator="\n", strip=True)

    lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if len(s) < 3:
            continue
        low = s.lower()
        if any(re.search(pat, low) for pat in _BOILERPLATE_PATTERNS):
            continue
        lines.append(s)

    return _clean_whitespace("\n".join(lines))

def get_text_from_url(url: str) -> str:
    """
    Fetch a URL and extract textual content.

    Handles:
    - Direct PDF links (application/pdf or *.pdf)
    - HTML pages (extract visible text, prefer <main>/<article>)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15"
        )
    }

    # Use timeouts to avoid hanging your agent
    resp = requests.get(url, headers=headers, timeout=(5, 25))
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")

    # PDF
    if _looks_like_pdf(content_type, url):
        return _clean_whitespace(extract_text_from_pdf_bytes(resp.content))

    # HTML/text
    resp.encoding = resp.encoding or "utf-8"
    html = resp.text

    try:

        summary_html = ReadabilityDoc(html).summary()
        extracted = _extract_text_from_html(summary_html)
        if extracted:
            return extracted
    except Exception:
        pass

    return _extract_text_from_html(html)

def url_ingestor(id: str, title: str, area: str, source: Dict[Literal["type", "url"], str]) -> Document:

    if source["type"] != "url":
        raise ValueError(f"Source type must be 'url', got {source['type']} instead.")
    
    ingest_warnings = []
    ingest_stats = {}

    extracted_text = get_text_from_url(source["url"])

    ingest_stats["n_chars"] = len(extracted_text)
    if len(extracted_text.strip()) == 0:
        ingest_warnings.append("URL content is empty.")
    
    document = Document(
        doc_id=id,
        title=title,
        area=area,
        source_type="url",
        source_uri=source["url"],
        content=extracted_text,
        page_map=[],
        ingest_warnings=ingest_warnings,
        ingest_stats=ingest_stats
    )
    return document