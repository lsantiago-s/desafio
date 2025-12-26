from ast import parse
import json
import logging
from typing import Iterable
from pydantic import BaseModel, Field, ValidationError
from agent.prompts import classifier_prompt
from agent.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from mcp_server.tools import Area
from agent.helper import get_config, make_llm, basic_parse_json, _safe_json_loads

logger = logging.getLogger(__name__)

class ClassifierOut(BaseModel):
    area: Area
    rationale: str = Field(default="")

    @staticmethod
    def validate_area(area: str, allowed: Iterable[str]) -> str:
        allowed_set = {a.strip() for a in allowed if a and a.strip()}
        if not allowed_set:
            return area.strip()
        candidate = area.strip()
        if candidate in allowed_set:
            return candidate
        return next(iter(sorted(allowed_set)))


def node_classify(state: AgentState, config: RunnableConfig | None=None) -> AgentState:
    cfg = get_config(config)
    llm = make_llm(cfg)

    areas = sorted({x["doc"]["area"] for x in state.retrieved if x.get("doc", {}).get("area")})
    if not areas:
        areas = Area.__args__
        state.warnings.append("Could not infer areas from retrieval; using placeholder labels.")

    retrieved_summaries = "\n\n".join(
        [
            f"- ({e['doc']['area']}) {e['doc']['title']} | score={e['hit'].get('score')}\n"
            f"  snippet: {e['doc']['content_snippet']}"
            for e in state.retrieved
        ]
    )[:6000]

    sys = SystemMessage(content=classifier_prompt(areas, retrieved_summaries))
    usr = HumanMessage(content=state.normalized_text[:7000])
    raw = llm.invoke([sys, usr]).content
    raw_json = basic_parse_json(raw)

    rationale = ""

    try:
        print(raw)
        parsed = ClassifierOut.model_validate(_safe_json_loads(raw_json))
        parsed.area = ClassifierOut.validate_area(parsed.area, areas)
        state.chosen_area = parsed.area
        rationale = (parsed.rationale or "").strip()
    except (ValidationError, json.JSONDecodeError) as e:
        state.warnings.append(f"Classifier JSON parse failed: {e}")
        state.chosen_area = areas[0]

    logger.info(f"Rationale: {rationale}")
    return state