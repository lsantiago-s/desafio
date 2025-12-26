
def classifier_prompt(areas: list[str], retrieved_summaries: str) -> str:
    areas_txt = ", ".join(areas)
    return f"""You are a scientific area classifier.

Choose exactly ONE label among: {areas_txt}

Use:
- the input article text (provided separately)
- the retrieved reference summaries below (from my private vector store)

Return ONLY a JSON object:
{{"area":"<one of the labels>","rationale":"<1-3 short sentences>"}}.

Retrieved references:
{retrieved_summaries}
"""


def extraction_prompt() -> str:
    key0 = f"what problem does the artcle propose to solve?"
    return f"""You are an information extractor.

Fill STRICTLY the JSON keys below (exact spelling, exact keys). Do not include any reasoning, explanations, markdown, or thinking process.
{{
  "{key0}": "",
  "step by step on how to solve it": ["", "", ""],
  "conclusion": ""
}}
"""


def review_prompt(chosen_area: str) -> str:
    return f"""You're a peer-reviewer who writes in Portuguese.

Context: the article was classified as **{chosen_area}**.

Write a short and objective review in Markdown with the rubric:
- Novelty/contribution
- Clarity and methodological quality
- Validity and threats (bias, data, assumptions, metrics, generalization)
- Reprodutibility (code, data, experimental details)
- Limitations and next steps
- If the article is not directly a Math, Medicine or Economics article, justify why label it as **{chosen_area}**.

Your review should be in Portuguese and follow the format below.

Formato:
## Resenha
**Pontos positivos:** ...
**Possíveis falhas:** ...
**Comentários finais:** ...
"""
