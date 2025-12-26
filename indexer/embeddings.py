# in: text data -> out: embedding vectors + metadata

# 1) Embedding model setting
import logging
from pydantic import BaseModel
from pathlib import Path
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingConfig(BaseModel):
    model_name: str
    normalize_embeddings: bool
    batch_size: int
    max_length: int
    device: str
    show_progress_bar: bool

# 2) Embedding interface
class Embedder:
    """Embedder using SentenceTransformer model."""
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model = SentenceTransformer(
            config.model_name, 
            device=config.device,
        )
        self.model.max_seq_length = self.config.max_length

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors."""
        embeddings = self.model.encode(
            texts, 
            batch_size=self.config.batch_size, 
            normalize_embeddings=self.config.normalize_embeddings,
            show_progress_bar=self.config.show_progress_bar,
            convert_to_numpy=True,
        )
        return embeddings.tolist()
    
    def info(self) -> dict:
        """Return information about the embedding model."""
        return {
            "model_name": self.config.model_name,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "normalize_embeddings": self.config.normalize_embeddings,
            "batch_size": self.config.batch_size,
            "device": self.config.device,
            "max_length": self.config.max_length
        }

    @staticmethod
    def from_manifest(manifest_path: str | Path) -> 'Embedder':
        """Create an Embedder from a manifest JSON file."""
        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = EmbeddingConfig(**data['embedding_config'])
        return Embedder(config)