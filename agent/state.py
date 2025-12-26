from dataclasses import dataclass, field
from typing import Any, Literal

InputKind = Literal["pdf", "url", "text"]
ExtractionKeys = Literal[
    "what problem does the artcle propose to solve?", 
    "step by step on how to solve it",
    "conclusion"
]

@dataclass
class AgentState:
    # input
    input_kind: InputKind
    input_value: str

    # pipeline
    normalized_text: str = ""
    retrieved: list[dict[str, Any]] = field(default_factory=list)
    chosen_area: str = ""
    extraction: dict[ExtractionKeys, Any] = field(default_factory=dict)
    review_markdown: str = ""

    # debug / hardening
    warnings: list[str] = field(default_factory=list)
    retrieval_debug: dict[str, Any] = field(default_factory=dict)