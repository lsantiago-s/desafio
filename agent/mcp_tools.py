import asyncio
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Coroutine
from concurrent.futures import Future
from agent.config import AgentConfig
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

_session: Optional[ClientSession] = None
_stdio_cm = None
_session_lock = asyncio.Lock()

_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None

@dataclass(frozen=True)
class MCPClientConfig:
    """
    Setting to launch FastMCP server over stdio.
    """
    command: str
    args: list[str]
    env: dict[str, str]

def _server_params_from_env() -> MCPClientConfig:
    cmd = os.getenv("MCP_SERVER_CMD", "python").strip()
    args_str = os.getenv("MCP_SERVER_ARGS", "scripts/call_mcp.py").strip()
    args = [a for a in args_str.split(" ") if a]
    env = dict(os.environ)

    return MCPClientConfig(command=cmd, args=args, env=env)

def _maybe_json(text: str) -> Any:
    text = text.strip()
    return json.loads(text)

def _unwrap_mcp_result(result: Any) -> Any:
    """
    Normalize MCP tool results to Python list/dict.
    """
    if isinstance(result, (list, dict)):
        return result
    
    if not result.content:
        return None

    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        first = content[0]
        text = getattr(first, "text", None)
        if isinstance(text, str) and text.strip():
            return _maybe_json(text)

    if isinstance(result, dict) and "content" in result:
        c = result["content"]
        if isinstance(c, list) and c:
            text = c[0].get("text")
            if isinstance(text, str):
                return _maybe_json(text)

    if hasattr(result, "__str__"):
        s = str(result)
        try:
            return _maybe_json(s)
        except Exception: 
            pass

    raise TypeError(f"Could not unwrap MCP tool result of type: {type(result)}")

def _require_keys(obj: dict[str, Any], keys: Iterable[str], *, where: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError(f"{where}: missing keys: {missing}. Got keys={list(obj.keys())}")

async def _get_session(cfg: AgentConfig) -> ClientSession:
    global _session, _stdio_cm

    async with _session_lock:
        if _session is not None:
            return _session

        launch = _server_params_from_env()
        server_params = StdioServerParameters(
            command=launch.command,
            args=launch.args,
            env=launch.env,
        )

        # Enter stdio_client context ONCE and keep it open
        _stdio_cm = stdio_client(server_params)
        read, write = await _stdio_cm.__aenter__()

        # Create and initialize session ONCE
        _session = ClientSession(read, write)
        await _session.__aenter__()
        await _session.initialize()
        return _session


async def close_mcp_session() -> None:
    """Call to avoid GC/__del__ issues."""
    global _session, _stdio_cm

    async with _session_lock:
        if _session is not None:
            await _session.__aexit__(None, None, None)
            _session = None
        if _stdio_cm is not None:
            await _stdio_cm.__aexit__(None, None, None)
            _stdio_cm = None

async def _call_tool(tool_name: str, args: dict[str, Any], cfg: AgentConfig) -> Any:
    """
    start stdio client, open session, initialize, call tool, close.
    """
    session = await _get_session(cfg)
    raw = await asyncio.wait_for(
        session.call_tool(tool_name, args),
        timeout=cfg.mcp_timeout_s
    )
    print(tool_name, args)
    return _unwrap_mcp_result(raw)


def search_articles(query: str, cfg: AgentConfig) -> list[dict[str, Any]]:
    """
    Calls MCP tool: search_articles(query: str) -> [{id,title,area,score}]
    """
    data = run_async(_call_tool("search_articles", {"query": query}, cfg))

    if not isinstance(data, list):
        raise TypeError(f"search_articles expected list, got {type(data)}")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise TypeError(f"search_articles hit[{i}] expected dict, got {type(item)}")
        _require_keys(item, ["id", "title", "area", "score"], where=f"search_articles hit[{i}]")

    return data


def get_article_content(article_id: str, cfg: AgentConfig) -> dict[str, Any]:
    """
    Calls MCP tool: get_article_content(id: str) -> {id,title,area,content}
    """
    data = run_async(_call_tool("get_article_content", {"id": article_id}, cfg))

    if not isinstance(data, dict):
        raise TypeError(f"get_article_content expected dict, got {type(data)}")

    _require_keys(data, ["id", "title", "area", "content"], where="get_article_content")
    return data

def _loop_worker(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()

def ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    if _loop is not None:
        return _loop

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=_loop_worker, args=(loop,), daemon=True)
    t.start()

    _loop = loop
    _thread = t
    return loop


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    loop = ensure_loop()
    fut: Future[Any] = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result()
