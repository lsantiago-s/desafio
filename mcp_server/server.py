from importlib import metadata
import os
import sys
import logging
from webbrowser import get
from fastmcp import FastMCP
from pathlib import Path
from mcp_server.storage import AppState, init_state
from mcp_server.tools import SearchHit, ArticleContent, get_article_content_impl, search_articles_impl

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

def _log_startup_config() -> None:
    chroma_dir = os.getenv("CHROMA_DIR", "data/chroma")
    collection_name = os.getenv("COLLECTION_NAME", "aaa")
    processed_dir = os.getenv("PROCESSED_DIR", "data/processed")
    articles_dir = os.getenv("ARTICLES_DIR", "data/articles")

    logger.info("Starting MCP server (FastMCP, stdio)")
    logger.info("Config: CHROMA_DIR=%s", chroma_dir)
    logger.info("Config: COLLECTION_NAME=%s", collection_name)
    logger.info("Config: PROCESSED_DIR=%s", processed_dir)
    

mcp = FastMCP(
    name="mcp-server"
)

_STATE: AppState | None = None

def _get_state() -> AppState:
    global _STATE
    if _STATE is None:
        chroma_dir = Path(os.getenv("CHROMA_DIR", "data/chroma"))
        collection_name = os.getenv("COLLECTION_NAME", "aaa")
        metadata_path = Path(os.getenv("ARTICLES_DIR", "data/articles")) / "metadata.json"
        manifest_path = Path(os.getenv("MANIFEST_PATH", "data/processed/manifest.json"))
        _STATE = init_state(
            chroma_dir=chroma_dir,
            collection_name=collection_name,
            metadata_path=metadata_path,
            manifest_path=manifest_path,
        )
    return _STATE

@mcp.tool
def search_articles(query: str) -> list[SearchHit]:
    """Search the indexed articles by similarity.

    Args:
        query (str): The search query string.

    Returns:
        list[SearchHit]: Doc-level search hits.
    """
    state = _get_state()
    return search_articles_impl(state, query)

@mcp.tool
def get_article_content(id: str) -> ArticleContent:
    """Retrieve content for a given document id.

    Args:
        id (str): The document id.

    Returns:
        ArticleContent: The content of the article.
    """
    state = _get_state()
    return get_article_content_impl(state, id)

if __name__ == "__main__":
    _log_startup_config()
    mcp.run()