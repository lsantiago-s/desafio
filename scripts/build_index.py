# arg parsing + chamar indexer.pipeline

import logging
import argparse
from indexer.pipeline import run_indexing_pipeline

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def main():
    parser = argparse.ArgumentParser(description="Build an index from various data sources.")
    parser.add_argument('--metadata-path', type=str, required=True)
    parser.add_argument('--chroma-dir', type=str, default='data/chroma')
    parser.add_argument('--processed-dir', type=str, default='data/processed')
    parser.add_argument('--collection', type=str, required=True)
    parser.add_argument('--chunk-size', type=int, required=True)
    parser.add_argument('--chunk-overlap', type=int, required=True)
    parser.add_argument('--reset', action='store_true', help='Reset existing index data if set.')
    parser.add_argument('--embedding-model', type=str, required=True, help='Embedding model name or path.')
    parser.add_argument('--normalize-embeddings', action='store_false', help='Whether to normalize embeddings.')
    parser.add_argument('--batch-size', type=int, help='Batch size for embedding generation.')
    parser.add_argument('--max-length', type=int, help='Maximum sequence length for embeddings.')
    parser.add_argument('--device', type=str, help='Device to run embedding model on.')
    parser.add_argument('--show-progress-bar', action='store_false', help='Show progress bar during embedding generation.')
    args = parser.parse_args()

    embedding_config = {
        "model_name": args.embedding_model,
        "normalize": args.normalize_embeddings,
        "batch_size": args.batch_size,
        "max_length": args.max_length,
        "device": args.device,
        "show_progress_bar": args.show_progress_bar
    }

    logger.info("Starting indexing pipeline...")
    run_indexing_pipeline(
        metadata_path=args.metadata_path,
        chroma_dir=args.chroma_dir,
        processed_dir=args.processed_dir,
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_config=embedding_config,
        reset=args.reset,
    )

if __name__ == "__main__":
    main()