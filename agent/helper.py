import json
import os
from typing import Any
from agent.config import AgentConfig
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

def make_llm(cfg: AgentConfig):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. "
            "Create an OpenAI API key and export it as OPENAI_API_KEY."
        )
    

    llm = ChatGoogleGenerativeAI(
        model=cfg.llm_model, 
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )
    return llm

def _safe_json_loads(text: str) -> Any:
    text = text.strip()
    return json.loads(text)

def get_config(config: RunnableConfig | None) -> AgentConfig:
    if not config:
        return AgentConfig()
    cfg = (config.get("configurable") or {}).get("cfg")
    return cfg if isinstance(cfg, AgentConfig) else AgentConfig()


def basic_parse_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("{") and raw.endswith("}"):
        return raw
    first = raw.find("{")
    last = raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        return raw[first:last+1]
    return raw