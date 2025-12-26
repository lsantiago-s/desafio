from typing import Any
from agent.mcp_tools import get_article_content, search_articles
from agent.state import AgentState
from langchain_core.runnables import RunnableConfig
from agent.helper import get_config

def node_retrieve(state: AgentState, config: RunnableConfig | None=None) -> AgentState:
    cfg = get_config(config)
    query = (state.normalized_text[:1500] or "").strip( )
    if not query:
        state.warnings.append("Empty normalized_text; cannot retrieve articles.")
        state.retrieved = []
        state.retrieval_debug = {"query": query, "hits": []}
        return state
    hits = search_articles(query=query, cfg=cfg)
    hits = hits[: cfg.top_k]
    state.retrieval_debug = {"query": query, "hits": hits}
    enriched: list[dict[str, Any]] = []
    for h in hits:
        try:
            doc = get_article_content(article_id=str(h["id"]), cfg=cfg)
            enriched.append(
                {
                    "hit": h,
                    "doc": {
                        "id": doc.get("id"),
                        "title": doc.get("title"),
                        "area": doc.get("area"),
                        "content_snippet": (doc.get("content") or "")[:1200],
                    },
                }
            )
        except Exception as e:
            state.warnings.append(f"Failed get_article_content for {h.get('id')}: {e}")
    state.retrieved = enriched
    return state
