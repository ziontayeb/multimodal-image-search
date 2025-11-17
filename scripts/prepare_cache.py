#!/usr/bin/env python3
"""
Prepare cache files for captions and enhanced queries.

This script pre-generates:
1. Image captions using Gemini vision API
2. Enhanced queries using Gemini text API

Results are cached to avoid repeated API calls during evaluation/search.
Includes rate limiting to respect free-tier API limits.
"""

from __future__ import annotations
import os
import sys
import json
import glob
import time
from pathlib import Path
from typing import Dict, Tuple, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from imagesearch.embeddings import file_id
from imagesearch.caption import describe_image, get_cached, put_cached
from imagesearch.enhance import enhance_query


# Configuration
IMAGES_DIR = "../example_images"
CAPTION_DB_PATH = "../data/captions/captions.json"
ENHANCED_DB_PATH = "../data/queries/enhanced_queries.json"
QUERIES_SPEC_PATH = "../data/queries/queries.json"

# Rate limiting (for Gemini free tier)
MAX_CALLS_PER_BATCH = 60
SLEEP_BETWEEN_CALLS = 1
SLEEP_AFTER_BATCH = 10


# Utility functions
def load_json(path: str) -> Dict[str, str]:
    """Load JSON file or return empty dict if not found."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: str, data: Dict[str, str]) -> None:
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# Caption generation
def list_all_images(images_dir: str) -> List[str]:
    """Find all images in directory."""
    exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    all_imgs: List[str] = []
    for ext in exts:
        all_imgs.extend(glob.glob(os.path.join(images_dir, f"*{ext}")))
        all_imgs.extend(glob.glob(os.path.join(images_dir, f"*{ext.upper()}")))
    return sorted(set(all_imgs))


def get_image_stem(path: str) -> str:
    """Extract filename without extension."""
    base = os.path.basename(path)
    stem, _ = os.path.splitext(base)
    return stem


def caption_needs_work(path: str, caption_db: Dict[str, str]) -> bool:
    """Check if caption is already cached."""
    stem = get_image_stem(path)
    if stem in caption_db and caption_db[stem]:
        return False

    fid = file_id(path)
    cached_cap = get_cached(fid)
    if cached_cap:
        return False

    return True


def store_caption_for_image(
    path: str,
    caption: str,
    caption_db: Dict[str, str]
) -> None:
    """Store caption in both cache and database."""
    fid = file_id(path)
    put_cached(fid, caption)
    stem = get_image_stem(path)
    caption_db[stem] = caption


def generate_missing_captions(images_dir: str) -> None:
    """
    Generate captions for all images that don't have them yet.
    Includes rate limiting and progress persistence.
    """
    caption_db = load_json(CAPTION_DB_PATH)
    all_imgs = list_all_images(images_dir)

    print(f"[Captions] Found {len(all_imgs)} images in {images_dir}")

    calls_in_current_batch = 0
    new_captions = 0

    for img_path in all_imgs:
        if not caption_needs_work(img_path, caption_db):
            continue

        # Rate limiting
        if calls_in_current_batch >= MAX_CALLS_PER_BATCH:
            print(f"[Captions] Batch limit reached, sleeping {SLEEP_AFTER_BATCH}s...")
            time.sleep(SLEEP_AFTER_BATCH)
            calls_in_current_batch = 0

        # Generate caption
        print(f"[Captions] Processing {img_path}...")
        try:
            cap_text, _usage = describe_image(img_path)
            store_caption_for_image(img_path, cap_text, caption_db)
            new_captions += 1
            calls_in_current_batch += 1

            # Gentle delay between calls
            time.sleep(SLEEP_BETWEEN_CALLS)

            # Persist incrementally
            save_json(CAPTION_DB_PATH, caption_db)

        except Exception as e:
            print(f"[Captions] Error processing {img_path}: {e}")
            continue

    print(f"[Captions] Done. {new_captions} new captions generated.")
    save_json(CAPTION_DB_PATH, caption_db)


# Enhanced query generation
def load_queries_spec(spec_path: str) -> Dict[str, dict]:
    """Load queries specification file."""
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def enhanced_query_needs_work(q_id: str, enhanced_db: Dict[str, str]) -> bool:
    """Check if enhanced query already exists."""
    return q_id not in enhanced_db or not enhanced_db[q_id]


def store_enhanced_query(
    q_id: str,
    enhanced_text: str,
    enhanced_db: Dict[str, str]
) -> None:
    """Store enhanced query in database."""
    enhanced_db[q_id] = enhanced_text


def generate_missing_enhanced_queries(spec_path: str) -> None:
    """
    Generate enhanced versions of all queries.
    Includes rate limiting and progress persistence.
    """
    if not os.path.exists(spec_path):
        print(f"[Enhance] Queries spec not found at {spec_path}, skipping.")
        return

    spec = load_queries_spec(spec_path)
    enhanced_db = load_json(ENHANCED_DB_PATH)

    # Flatten queries
    todo: List[Tuple[str, str]] = []
    for bucket in spec.values():
        q_block = bucket.get("queries", {})
        for q_id, q_text in q_block.items():
            todo.append((q_id, q_text))

    print(f"[Enhance] Found {len(todo)} queries")

    calls_in_current_batch = 0
    new_queries = 0

    for q_id, q_text in todo:
        if not enhanced_query_needs_work(q_id, enhanced_db):
            continue

        # Rate limiting
        if calls_in_current_batch >= MAX_CALLS_PER_BATCH:
            print(f"[Enhance] Batch limit reached, sleeping {SLEEP_AFTER_BATCH}s...")
            time.sleep(SLEEP_AFTER_BATCH)
            calls_in_current_batch = 0

        # Generate enhanced query
        print(f"[Enhance] Processing {q_id}: \"{q_text}\"...")
        try:
            enhanced_text = enhance_query(q_text)
            store_enhanced_query(q_id, enhanced_text, enhanced_db)
            new_queries += 1
            calls_in_current_batch += 1

            # Slightly longer delay for text generation
            time.sleep(2 * SLEEP_BETWEEN_CALLS)

            # Persist incrementally
            save_json(ENHANCED_DB_PATH, enhanced_db)

        except Exception as e:
            print(f"[Enhance] Error processing {q_id}: {e}")
            continue

    print(f"[Enhance] Done. {new_queries} new enhanced queries generated.")
    save_json(ENHANCED_DB_PATH, enhanced_db)


# Main
def main():
    """Main entry point."""
    print("=" * 60)
    print("Cache Preparation Script")
    print("=" * 60)

    # Generate captions
    if os.path.exists(IMAGES_DIR):
        generate_missing_captions(IMAGES_DIR)
    else:
        print(f"[Warning] Images directory not found: {IMAGES_DIR}")

    # Generate enhanced queries
    generate_missing_enhanced_queries(QUERIES_SPEC_PATH)

    print("\n" + "=" * 60)
    print("Cache preparation complete!")
    print(f"Captions: {CAPTION_DB_PATH}")
    print(f"Enhanced queries: {ENHANCED_DB_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()