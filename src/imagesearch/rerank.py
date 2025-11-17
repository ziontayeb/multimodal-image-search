"""Caption-based reranking for improved search results."""

from __future__ import annotations
from typing import List, Dict, Any, Callable

import numpy as np

from .embeddings import encode_text_clip, encode_texts_clip


def rerank_by_caption(
    query: str,
    matches: List[Dict[str, Any]],
    get_caption: Callable[[str], str],
    alpha: float = 0.6,
    use_blend: bool = True
) -> List[Dict[str, Any]]:
    """
    Rerank search results using caption similarity in CLIP text space.

    This performs a two-stage retrieval:
    1. Initial retrieval using reduced-dimension CLIP embeddings
    2. Reranking using full-dimension CLIP text embeddings of captions

    Args:
        query: Text query
        matches: Initial search results from Pinecone with keys: id, score, metadata
        get_caption: Function to retrieve caption for an image path
        alpha: Blend weight for caption similarity (0.0 = only orig score, 1.0 = only caption)
        use_blend: If True, blend original and caption scores. If False, use only caption score.

    Returns:
        List of reranked results sorted by final_score (descending)
    """
    if not matches:
        return []

    # Extract paths and get captions
    paths = [m["metadata"].get("path", "") for m in matches]
    captions = [get_caption(p) if p else "" for p in paths]

    # Compute caption similarities in full CLIP text space (768-d)
    q = encode_text_clip(query)  # (768,)
    caps = encode_texts_clip(captions)  # (K, 768)
    cap_sims = caps @ q  # Cosine similarity (already normalized)

    # Compute final scores
    out = []
    for m, cap, cs in zip(matches, captions, cap_sims):
        orig = float(m.get("score", 0.0))

        if use_blend:
            # Rescale original score from [0, 1] to [-1, 1] for blending
            orig_rescaled = (2.0 * orig) - 1.0
            final = (1.0 - alpha) * orig_rescaled + alpha * float(cs)
        else:
            # Pure caption-based ranking
            final = float(cs)

        out.append({
            "final_score": final,
            "orig_score": orig,
            "caption_sim": float(cs),
            "path": m["metadata"].get("path", ""),
            "id": m["id"],
            "caption": cap,
        })

    # Sort by final score (descending)
    out.sort(key=lambda r: r["final_score"], reverse=True)
    return out