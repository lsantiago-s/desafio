import argparse
import json
from pathlib import Path
from agent.config import AgentConfig
from agent.graph import build_graph
from agent.state import AgentState

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-kind", choices=["text", "url", "pdf"], required=True)
    ap.add_argument("--input", required=True, help="raw text, url, or path")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--article-key-typo", choices=["artcle", "article"], default="artcle")
    args = ap.parse_args()

    cfg = AgentConfig()

    graph = build_graph()

    state = AgentState(input_kind=args.input_kind, input_value=args.input)
    final_state = graph.invoke(state, config={"configurable": {"cfg": cfg}})  # langgraph compatible
    
    area = final_state.get("chosen_area", "") or final_state.get("area", "")
    extraction = final_state.get("extraction", {})
    review_md = final_state.get("review_markdown", "")
    warnings = final_state.get("warnings", [])


    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "extraction_1.json").write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "review_1.md").write_text(review_md, encoding="utf-8")

    result_verbose = {
        "area": area,
        "extraction": extraction,
        "review_markdown": review_md,
        "warnings": warnings,
    }
    agent_output = {
        "area": area,
        "extraction": extraction,
        "review_markdown": review_md,
    }
    (out_dir / "agent_output.json").write_text(
        json.dumps(agent_output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result_verbose, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
