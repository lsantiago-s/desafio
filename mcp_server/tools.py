from collections import defaultdict
from typing import Literal, Any
from pydantic import BaseModel
from mcp_server.storage import AppState

Area = Literal["Mathematics", "Medicine", "Economics"]

class SearchHit(BaseModel):
    id: str
    title: str
    area: Area
    score: float

class ArticleContent(BaseModel):
    id: str
    title: str
    area: Area
    content: str

def _distance_to_score(distance: float) -> float:
    # define score
    s = distance
    return s

def search_articles_impl(state: AppState, query: str, *, k_chunks: int=60, k_docs: int=5) -> list[SearchHit]:
    q = (query or "").strip()
    if not q:
        return []
    
    q_emb = state.embed_query(q)
    res = state.collection.query(
        query_embeddings=[q_emb],
        n_results=k_chunks,
        include=['distances', 'metadatas']
    )

    metadatas: list[dict[str, Any]] = (res.get("metadatas") or [[]])[0]
    distances: list[float] = (res.get("distances") or [[]])[0]

    per_doc_scores: dict[str, list[float]] = defaultdict(list)
    per_doc_area: dict[str, Area] = {}

    for md, dist in zip(metadatas, distances):
        doc_id = md.get("doc_id")
        if not doc_id:
            continue
        per_doc_scores[doc_id].append(_distance_to_score(dist))
        if doc_id not in per_doc_area:
            per_doc_area[doc_id] = md.get("area", "Unknown")

    doc_hits: list[tuple[str, float]] = []
    for doc_id, scores in per_doc_scores.items():
        top = sorted(scores, reverse=True)[:k_chunks]
        score_doc = sum(top) / max(len(top), 1)
        doc_hits.append((doc_id, score_doc))

    doc_hits.sort(key=lambda x: x[1], reverse=True)
    doc_hits = doc_hits[:k_docs]

    out: list[SearchHit] = []
    for doc_id, score in doc_hits:
        meta = state.doc_meta.get(doc_id)
        title = meta.title if meta else doc_id
        area = meta.area if meta else per_doc_area.get(doc_id, "Unknown")
        out.append(SearchHit(id=doc_id, title=title, area=area, score=float(score)))

    return out

def get_article_content_impl(state: AppState, doc_id: str, *, max_chunks: int=100, max_chars: int=40000) -> ArticleContent:
    did = (doc_id or "").strip()
    if not did:
        raise ValueError("Invalid doc_id")
    
    res = state.collection.get(
        where={"doc_id": did},
        include=['documents', 'metadatas'],
    )

    docs: list[str] = res.get("documents", [])
    metadatas: list[dict[str, Any]] = res.get("metadatas", [])

    if not docs:
        meta = state.doc_meta.get(did)
        return ArticleContent(
            id=did,
            title=meta.title if meta else did,
            area=meta.area if meta else "Unknown",
            content=""
        )
    
    rows = []
    for text, md in zip(docs, metadatas):
        page = md.get("page_start", md.get("page"))
        cs = md.get("char_start", md.get("char"))
        ce = md.get("char_end")
        rows.append((page or 0, cs or 0, ce or 0, text, md))

    rows.sort(key=lambda x: (x[0], x[1]))

    parts: list[str] = []
    total = 0
    for page, cs, ce, text, md in rows[:max_chunks]:
        header = f"[doc_id={did} page={page} chars={cs}-{ce}]\n"
        chunk = f"{header}{text}\n\n"
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk) + 2

    meta = state.doc_meta.get(did)
    area = meta.area if meta else (rows[0][4].get("area", "Unknown") if rows else "Unknown")
    title = meta.title if meta else 'unknown'

    return ArticleContent(
        id=did,
        title=title,
        area=area,
        content="".join(parts)
    )