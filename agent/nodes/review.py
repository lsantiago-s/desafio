import json
from pydantic import BaseModel, Field, ValidationError, field_validator
from agent.prompts import review_prompt
from agent.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from agent.helper import get_config, make_llm

class ReviewOut(BaseModel):
    review_markdown: str = Field(default="")

    @field_validator("review_markdown")
    @classmethod
    def _strip_and_require_str(cls, v: object) -> str:
        if v is None:
            return ""
        if not isinstance(v, str):
            raise TypeError("review_markdown must be a string")
        return v.strip()

    @staticmethod
    def ensure_min_sections(md: str) -> str:
        """
        Soft hardening: ensure the review contains the minimum structure
        expected by the challenge (in Portuguese).
        """
        md = (md or "").strip()

        has_title = "## Resenha" in md
        has_pos = "**Pontos positivos:**" in md
        has_neg = "**Possíveis falhas:**" in md

        if has_title and has_pos and has_neg:
            return md

        scaffold = (
            "## Resenha\n"
            "**Pontos positivos:** \n\n"
            "**Possíveis falhas:** \n\n"
            "**Comentários finais:** \n\n"
        )

        if not md:
            return scaffold

        return scaffold + "\n" + md



def parse_review(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("## Resenha"):
        return raw

    first = raw.find("## Resenha")
    if first != -1:
        return raw[first:]
    return raw

def node_review(state: AgentState, cfg: RunnableConfig | None=None) -> AgentState:
    cfg = get_config(cfg)
    llm = make_llm(cfg)
    sys = SystemMessage(content=review_prompt(state.chosen_area or "N/A"))

    if state.extraction is None:
        state.warnings.append("No extraction data available for review.")
        state.review_markdown = ""
        return state

    usr = HumanMessage(
        content=(
            "Review content:\n\n"
            f"=== EXTRACTION (JSON) ===\n{json.dumps(state.extraction, ensure_ascii=False)}\n\n"
            "=== ARTICLE TEXT (excerpt) ===\n"
            f"{state.normalized_text[:9000]}"
        )
    )

    raw = parse_review(llm.invoke([sys, usr]).content)
    raw_parsed = parse_review(raw)
    try:
        review = ReviewOut.model_validate({"review_markdown": raw_parsed})
        raw_parsed = ReviewOut.ensure_min_sections(review.review_markdown)
    except ValidationError as e:
        state.warnings.append(f"Review validation failed: {e}")
        raw_parsed = ReviewOut.ensure_min_sections(raw_parsed)
    state.review_markdown = raw_parsed
    return state