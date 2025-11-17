"""CLIP embeddings with random projection for dimensionality reduction."""

from __future__ import annotations
import hashlib
import os
from typing import Iterable

import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer

from .config import CLIP_MODEL, REDUCE_DIM, RP_MATRIX_PATH


# Device selection
def _get_device() -> str:
    """Select the best available device for inference."""
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"


DEVICE = _get_device()
_model = SentenceTransformer(CLIP_MODEL, device=DEVICE)


# Random Projection utilities
def ensure_rp_matrix() -> np.ndarray:
    """
    Load or create a Random Projection matrix for dimensionality reduction.

    Returns:
        Random projection matrix of shape (512, REDUCE_DIM)
    """
    if os.path.exists(RP_MATRIX_PATH):
        return np.load(RP_MATRIX_PATH)

    rng = np.random.default_rng(42)
    R = rng.normal(0.0, 1.0, size=(512, REDUCE_DIM)).astype(np.float32)
    np.save(RP_MATRIX_PATH, R)
    print(f"[RP] Created matrix {R.shape}, saved to {RP_MATRIX_PATH}")
    return R


def rp_project_and_norm(vecs: np.ndarray, R: np.ndarray) -> np.ndarray:
    """
    Apply random projection and normalize the vectors.

    Args:
        vecs: Input vectors of shape (N, 512) or (512,)
        R: Random projection matrix of shape (512, REDUCE_DIM)

    Returns:
        Projected and normalized vectors of shape (N, REDUCE_DIM)
    """
    if vecs.ndim == 1:
        vecs = vecs.reshape(1, -1)

    # Project to lower dimension
    X = vecs @ R
    X = X / np.sqrt(REDUCE_DIM, dtype=np.float32)

    # Normalize
    norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
    return X / norms


# File utilities
def file_id(path: str) -> str:
    """
    Generate a unique hash ID for a file based on its content.

    Args:
        path: Path to the file

    Returns:
        SHA-1 hexdigest of the file content
    """
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_image(path: str) -> Image.Image:
    """
    Load an image from disk and convert to RGB.

    Args:
        path: Path to the image file

    Returns:
        PIL Image in RGB format
    """
    return Image.open(path).convert("RGB")


# Encoding functions
def encode_images(paths: Iterable[str], batch_size: int = 16) -> np.ndarray:
    """
    Encode multiple images to reduced-dimension embeddings.

    Args:
        paths: Iterable of image file paths
        batch_size: Batch size for encoding

    Returns:
        Array of embeddings with shape (N, REDUCE_DIM)
    """
    R = ensure_rp_matrix()
    imgs = [load_image(p) for p in paths]
    embs512 = _model.encode(
        imgs,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return rp_project_and_norm(embs512, R)


def encode_image(path: str) -> np.ndarray:
    """
    Encode a single image to reduced-dimension embedding.

    Args:
        path: Path to the image file

    Returns:
        Embedding vector of shape (REDUCE_DIM,)
    """
    R = ensure_rp_matrix()
    img = load_image(path)
    emb512 = _model.encode(img, convert_to_numpy=True, normalize_embeddings=True)
    return rp_project_and_norm(emb512, R)[0]


def encode_text_to_index(text: str) -> np.ndarray:
    """
    Encode text to reduced-dimension embedding for indexing/search.

    Args:
        text: Query text

    Returns:
        Embedding vector of shape (REDUCE_DIM,)
    """
    R = ensure_rp_matrix()
    q512 = _model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return rp_project_and_norm(q512, R)[0]


def encode_text_clip(text: str) -> np.ndarray:
    """
    Encode text to full 512-d CLIP embedding (no random projection).
    Used for caption-based reranking.

    Args:
        text: Text to encode

    Returns:
        Embedding vector of shape (512,)
    """
    return _model.encode(text, convert_to_numpy=True, normalize_embeddings=True)


def encode_texts_clip(texts: list[str]) -> np.ndarray:
    """
    Encode multiple texts to full 512-d CLIP embeddings (no random projection).

    Args:
        texts: List of texts to encode

    Returns:
        Array of embeddings with shape (N, 512)
    """
    return _model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)