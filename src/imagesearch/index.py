"""Pinecone vector index management for image search."""

from __future__ import annotations
import glob
import os
from typing import List, Dict, Any

from pinecone import Pinecone, ServerlessSpec

from .config import INDEX_NAME, PINECONE_CLOUD, PINECONE_REGION, REDUCE_DIM
from .embeddings import encode_image, encode_images, encode_text_to_index, file_id


# Initialize Pinecone client
def _get_pinecone_client() -> Pinecone:
    """Initialize and return Pinecone client."""
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PINECONE_API_KEY not found in environment. "
            "Please set it in your .env file."
        )
    return Pinecone(api_key=api_key)


# Initialize index
pc = _get_pinecone_client()

if INDEX_NAME not in {ix.name for ix in pc.list_indexes()}:
    print(f"Creating new index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=REDUCE_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )

index = pc.Index(INDEX_NAME)


def upsert_one(path: str) -> str:
    """
    Insert or update a single image in the index.

    Args:
        path: Path to the image file

    Returns:
        Vector ID (file hash)
    """
    vec = encode_image(path)
    vid = file_id(path)
    index.upsert([{
        "id": vid,
        "values": vec.tolist(),
        "metadata": {"path": path}
    }])
    return vid


def upsert_dir(folder: str, batch_size: int = 16) -> int:
    """
    Insert or update all images in a directory.

    Args:
        folder: Path to the directory containing images
        batch_size: Number of images to process in each batch

    Returns:
        Total number of images upserted
    """
    patterns = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    files = sorted({
        p for pat in patterns
        for p in glob.glob(os.path.join(folder, pat))
    })

    if not files:
        print(f"No image files found in {folder}")
        return 0

    total = 0
    for i in range(0, len(files), batch_size):
        group = files[i:i + batch_size]
        embs = encode_images(group, batch_size=batch_size)

        upserts = [{
            "id": file_id(p),
            "values": e.tolist(),
            "metadata": {"path": p}
        } for p, e in zip(group, embs)]

        index.upsert(upserts)
        total += len(upserts)
        print(f"Upserted batch {i // batch_size + 1}: {len(upserts)} images")

    return total


def delete_by_path(path: str) -> None:
    """
    Delete an image from the index by its file path.

    Args:
        path: Path to the image file
    """
    index.delete(filter={"path": {"$eq": path}})


def search(query: str, top_k: int) -> List[Dict[str, Any]]:
    """
    Search for images matching a text query.

    Args:
        query: Text query
        top_k: Number of results to return

    Returns:
        List of matches with id, score, and metadata
    """
    q = encode_text_to_index(query)
    res = index.query(
        vector=q.tolist(),
        top_k=top_k,
        include_metadata=True
    )
    return res.get("matches", [])


def stats() -> Dict[str, Any]:
    """
    Get index statistics.

    Returns:
        Dictionary containing index stats
    """
    return index.describe_index_stats()


def wipe() -> None:
    """Delete all vectors from the index."""
    index.delete(delete_all=True)
    print(f"Wiped all vectors from index: {INDEX_NAME}")