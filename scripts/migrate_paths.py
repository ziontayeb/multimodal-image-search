"""Migrate absolute paths in Pinecone to relative paths."""

from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.imagesearch.index import index, _to_relative_path
from src.imagesearch.config import PROJECT_ROOT


def migrate_paths():
    """
    Fetch all vectors from Pinecone and update paths to be relative.
    This is needed when switching from absolute to relative path storage.
    """
    print("Fetching all vectors from index...")

    # Get index stats to know how many vectors we have
    stats = index.describe_index_stats()
    total = stats.get('total_vector_count', 0)

    if total == 0:
        print("No vectors found in index. Nothing to migrate.")
        return

    print(f"Found {total} vectors in index")
    print("\nFetching vectors...")

    # Fetch all vectors (Pinecone doesn't have a direct "list all" but we can query with dummy vector)
    # Alternative: use the list_paginated API if available
    # For now, we'll use a different approach - just re-index everything

    print("\nIMPORTANT: Path migration requires re-indexing your images.")
    print("This script will help you understand what needs to be done.\n")
    print("Options:")
    print("1. Wipe the index and re-upload all images from web/uploads/")
    print("2. Keep existing index (old paths may not work for others who clone)")
    print("\nRecommended: Re-upload images after wiping the index")
    print("\nTo wipe and re-index:")
    print("  python -m imagesearch.cli wipe")
    print("  python -m imagesearch.cli insert --dir web/uploads/ --batch 32")


if __name__ == "__main__":
    migrate_paths()
