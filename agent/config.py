from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class AgentConfig:
    top_k: int = 5
    mcp_timeout_s: float = 20.0
    # Choose provider: "openai" or "huggingface"
    llm_provider: Literal["openai","huggingface"] = "openai"

    # OpenAI (only used if llm_provider="openai")
    llm_model: str = "gemini-2.0-flash"

    # Hugging Face (used if llm_provider="huggingface")
    hf_repo_id: str = "deepseek-ai/DeepSeek-R1-0528"
    hf_provider: str = "auto"
    hf_task: str = "text-generation"
    hf_max_new_tokens: int = 512
    hf_do_sample: bool = False
    hf_repetition_penalty: float = 1.03

    temperature: float = 0.2
    mcp_timeout_s: float = 10.0
    max_tokens=3200
