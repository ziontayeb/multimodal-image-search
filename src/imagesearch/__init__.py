"""
Image Search System using CLIP embeddings and Pinecone vector database.

This package provides:
- CLIP-based image and text embeddings
- Pinecone vector index management
- Gemini-powered image captioning and query enhancement
- Caption-based reranking for improved search results
"""

from .config import (
    REDUCE_DIM,
    INDEX_NAME,
    CLIP_MODEL,
    GEMINI_MODEL,
)
from .index import (
    upsert_one,
    upsert_dir,
    search,
    delete_by_path,
    wipe,
    stats,
)
from .embeddings import (
    encode_image,
    encode_images,
    encode_text_to_index,
    encode_text_clip,
    file_id,
)
from .caption import (
    describe_image,
    load_caption_db,
    offline_caption_getter,
    get_cached as get_cached_caption,
    put_cached as put_cached_caption,
)
from .enhance import (
    enhance_query,
    load_enhanced_db,
    get_used_query,
)
from .rerank import rerank_by_caption

__version__ = "1.0.0"

__all__ = [
    # Config
    "REDUCE_DIM",
    "INDEX_NAME",
    "CLIP_MODEL",
    "GEMINI_MODEL",
    # Index operations
    "upsert_one",
    "upsert_dir",
    "search",
    "delete_by_path",
    "wipe",
    "stats",
    # Embeddings
    "encode_image",
    "encode_images",
    "encode_text_to_index",
    "encode_text_clip",
    "file_id",
    # Captions
    "describe_image",
    "load_caption_db",
    "offline_caption_getter",
    "get_cached_caption",
    "put_cached_caption",
    # Query enhancement
    "enhance_query",
    "load_enhanced_db",
    "get_used_query",
    # Reranking
    "rerank_by_caption",
]