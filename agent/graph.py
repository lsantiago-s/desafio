
from typing import Any
from agent.nodes.classify import node_classify
from agent.nodes.extract import node_extract
from agent.nodes.normalize import node_normalize_input
from agent.nodes.retrieve import node_retrieve
from agent.nodes.review import node_review
from agent.state import AgentState
from langgraph.graph import StateGraph, END


def build_graph() -> Any:
    g = StateGraph(AgentState)
    g.add_node("normalize", node_normalize_input)
    g.add_node("retrieve", node_retrieve)
    g.add_node("classify", node_classify)
    g.add_node("extract", node_extract)
    g.add_node("review", node_review)

    g.set_entry_point("normalize")
    g.add_edge("normalize", "retrieve")
    g.add_edge("retrieve", "classify")
    g.add_edge("classify", "extract")
    g.add_edge("extract", "review")
    g.add_edge("review", END)

    return g.compile()
