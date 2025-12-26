import json
from typing import Any
from pydantic import BaseModel, ValidationError, field_validator
from agent.prompts import extraction_prompt
from agent.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from agent.helper import get_config, make_llm, basic_parse_json, _safe_json_loads

class ExtractionOut(BaseModel):
    """
    Wraps the strict extraction JSON required by the challenge.

    `data` MUST be a dict with EXACTLY:
      - "what problem does the artcle propose to solve?"
      - "step by step on how to solve it"  (list of len 3)
      - "conclusion"
    """

    data: dict[str, Any]

    @field_validator("data")
    @classmethod
    def _validate_data_is_dict(cls, v: Any) -> dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("ExtractionOut.data must be a dict")
        return v

    @staticmethod
    def expected_keys() -> list[str]:
        return [
            "what problem does the artcle propose to solve?",
            "step by step on how to solve it",
            "conclusion",
        ]

    @classmethod
    def coerce_and_validate(cls, payload: Any) -> "ExtractionOut":
        """
        Best-effort coercion into the exact schema.
        Raises ValidationError only if payload is wildly incompatible.
        """
        expected = cls.expected_keys()

        if not isinstance(payload, dict):
            payload = {}

        coerced: dict[str, Any] = {
            expected[0]: payload.get(expected[0], ""),
            expected[1]: payload.get(expected[1], ["", "", ""]),
            expected[2]: payload.get(expected[2], ""),
        }
        steps = coerced[expected[1]]
        if not isinstance(steps, list):
            steps = ["", "", ""]
        steps = [str(s) if s is not None else "" for s in steps]
        steps = (steps + ["", "", ""])[:3]
        coerced[expected[1]] = steps

        coerced[expected[0]] = str(coerced[expected[0]] or "")
        coerced[expected[2]] = str(coerced[expected[2]] or "")

        return cls(data=coerced)

    @classmethod
    def needs_repair(cls, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return True
        expected = set(cls.expected_keys())
        return set(payload.keys()) != expected


def node_extract(state: AgentState, cfg: RunnableConfig | None=None) -> AgentState:
    
    cfg = get_config(cfg)
    llm = make_llm(cfg)
    sys = SystemMessage(content=extraction_prompt())
    usr = HumanMessage(content=state.normalized_text[:12000])

    raw = llm.invoke([sys, usr]).content
    raw_parsed = basic_parse_json(raw)
    try:
        data = _safe_json_loads(raw_parsed)
    except json.JSONDecodeError as e:
        state.warnings.append(f"Extractor returned invalid JSON: {e}")
        data = {}

    if ExtractionOut.needs_repair(data):
        expected = ExtractionOut.expected_keys()
        repair_prompt = (
        "Return ONLY valid JSON.\n"
        "Use EXACTLY these keys:\n"
        f"{json.dumps(expected, ensure_ascii=False)}\n\n"
        "Do not change the language of the values.\n\n"
        "Here is your previous output (may be invalid JSON). Convert it to valid JSON with the keys above:\n"
        f"{raw}"
    )
        raw2 = llm.invoke([SystemMessage(content=repair_prompt)]).content
        try:
            data = _safe_json_loads(raw2)
        except json.JSONDecodeError as e:
            state.warnings.append(f"Extractor repair failed: {e}")
            data = {}

    try:
        extraction = ExtractionOut.coerce_and_validate(data)
        state.extraction = extraction.data
    except ValidationError as e:
        state.warnings.append(f"Extractor final validation failed: {e}")
        state.extraction = ExtractionOut.coerce_and_validate({}).data
    return state