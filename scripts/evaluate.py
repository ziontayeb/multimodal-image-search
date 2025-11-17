#!/usr/bin/env python3
"""
Evaluation script for image search system.

Runs evaluation across different model configurations:
- Models: clip, clip_rerank (alpha=1.0, 0.6, 0.4)
- Enhancement: enabled/disabled
- Queries: easy (eq), medium (mq), hard (hq)
- Various k values per difficulty

Outputs results to CSV for analysis.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from imagesearch import index
from imagesearch.embeddings import file_id
from imagesearch.caption import describe_image, get_cached, put_cached
from imagesearch.enhance import enhance_query
from imagesearch.rerank import rerank_by_caption
from imagesearch.config import DATA_DIR


# Paths
QUERIES_PATH = DATA_DIR / "queries" / "queries.json"
ENHANCED_CACHE_PATH = DATA_DIR / "queries" / "enhanced_cache.json"
EVALUATION_DIR = DATA_DIR / "evaluation"
EVALUATION_DIR.mkdir(parents=True, exist_ok=True)


def load_queries() -> Dict[str, Any]:
    """Load queries from JSON file."""
    with open(QUERIES_PATH, "r") as f:
        return json.load(f)


def load_enhanced_cache() -> Dict[str, str]:
    """Load cached enhanced queries."""
    if ENHANCED_CACHE_PATH.exists():
        with open(ENHANCED_CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_enhanced_cache(cache: Dict[str, str]) -> None:
    """Save enhanced queries to cache."""
    ENHANCED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ENHANCED_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_enhanced_query(query_id: str, query_text: str, cache: Dict[str, str]) -> str:
    """
    Get enhanced query, using cache if available.

    Args:
        query_id: Query identifier (e.g., "eq1")
        query_text: Original query text
        cache: Enhanced query cache

    Returns:
        Enhanced query text
    """
    if query_id in cache:
        return cache[query_id]

    print(f"  Enhancing query '{query_id}': {query_text}")
    enhanced = enhance_query(query_text)
    cache[query_id] = enhanced
    save_enhanced_cache(cache)
    print(f"    → {enhanced}")
    return enhanced


def get_caption_cached(path: str) -> str:
    """
    Get caption for an image, using cache when available.
    Generates with Gemini if not cached.

    Args:
        path: Path to the image file (may be relative)

    Returns:
        Image caption
    """
    # Convert to absolute path if relative
    if not os.path.isabs(path):
        path = str(project_root / path)

    # Check if file exists
    if not os.path.exists(path):
        print(f"    Warning: File not found: {path}")
        return ""

    key = file_id(path)
    cap = get_cached(key)
    if cap:
        return cap

    print(f"    Generating caption for: {path}")
    cap, _ = describe_image(path)
    put_cached(key, cap)
    return cap


def extract_image_name(path: str) -> str:
    """
    Extract image name from path.

    Example: "data/example_images/eq1_1.jpg" -> "eq1_1"

    Args:
        path: Full image path

    Returns:
        Image name without extension
    """
    basename = os.path.basename(path)
    name, _ = os.path.splitext(basename)
    return name


def run_search(
    query: str,
    k: int,
    model: str,
    alpha: float = 0.6,
    expand: int = 3
) -> List[str]:
    """
    Run search with specified configuration.

    Args:
        query: Query text (original or enhanced)
        k: Number of results to return
        model: Model type ("clip" or "clip_rerank")
        alpha: Blend weight for reranking (only used if model="clip_rerank")
        expand: Expansion factor for initial retrieval

    Returns:
        List of image names (e.g., ["eq1_1", "eq1_2", ...])
    """
    # Fetch expand*k results from Pinecone
    fetch_k = max(1, k * expand)
    matches = index.search(query, fetch_k)

    if not matches:
        return []

    # Apply reranking if needed
    if model == "clip_rerank":
        reranked = rerank_by_caption(
            query,
            matches,
            get_caption_cached,
            alpha=alpha,
            use_blend=True
        )
        # Take top k from reranked results
        results = reranked[:k]
        paths = [r["path"] for r in results]
    else:
        # Just take top k from initial results
        results = matches[:k]
        paths = [m["metadata"].get("path", "") for m in results]

    # Extract image names
    return [extract_image_name(p) for p in paths if p]


def run_evaluation(
    output_file: str,
    expand: int = 3,
    models: List[str] = None,
    difficulties: List[str] = None
) -> None:
    """
    Run full evaluation and save results to CSV.

    Args:
        output_file: Output CSV file path
        expand: Expansion factor for initial retrieval (default: 3)
        models: List of models to evaluate (default: all)
        difficulties: List of difficulties to evaluate (default: all)
    """
    # Load queries
    queries_data = load_queries()
    enhanced_cache = load_enhanced_cache()

    # Default configurations
    if models is None:
        models = ["clip", "clip_rerank"]

    if difficulties is None:
        difficulties = ["eq", "mq", "hq"]

    # Model configurations
    model_configs = {
        "clip": [(False, None)],  # No reranking, alpha is None
        "clip_rerank": [
            (True, 1.0),   # alpha=1.0 (pure caption)
            (True, 0.6),   # alpha=0.6 (blend)
            (True, 0.4),   # alpha=0.4 (blend)
        ]
    }

    # Enhancement settings
    enhancement_settings = [True, False]

    # Open CSV for writing
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "enhancement", "difficulty", "query_id", "k", "results"])

        total_runs = 0
        for model in models:
            for use_enhancement in enhancement_settings:
                for difficulty in difficulties:
                    if difficulty not in queries_data:
                        print(f"Warning: Difficulty '{difficulty}' not found in queries")
                        continue

                    diff_data = queries_data[difficulty]
                    k_vals = diff_data["k_vals"]
                    queries = diff_data["queries"]

                    for query_id, query_text in queries.items():
                        # Get query to use (original or enhanced)
                        if use_enhancement:
                            used_query = get_enhanced_query(query_id, query_text, enhanced_cache)
                        else:
                            used_query = query_text

                        for k in k_vals:
                            # For clip_rerank, try each alpha value
                            if model == "clip_rerank":
                                for is_rerank, alpha in model_configs[model]:
                                    model_name = f"clip_rerank_a{alpha}"

                                    print(f"Running: {model_name}, enhancement={use_enhancement}, "
                                          f"{difficulty}, {query_id}, k={k}")

                                    results = run_search(
                                        used_query,
                                        k,
                                        "clip_rerank",
                                        alpha=alpha,
                                        expand=expand
                                    )

                                    # Write to CSV
                                    writer.writerow([
                                        model_name,
                                        use_enhancement,
                                        difficulty,
                                        query_id,
                                        k,
                                        json.dumps(results)  # Store as JSON array
                                    ])
                                    total_runs += 1

                            # For clip, just run once
                            else:
                                print(f"Running: {model}, enhancement={use_enhancement}, "
                                      f"{difficulty}, {query_id}, k={k}")

                                results = run_search(
                                    used_query,
                                    k,
                                    model,
                                    expand=expand
                                )

                                # Write to CSV
                                writer.writerow([
                                    model,
                                    use_enhancement,
                                    difficulty,
                                    query_id,
                                    k,
                                    json.dumps(results)  # Store as JSON array
                                ])
                                total_runs += 1

        print(f"\n✓ Evaluation complete!")
        print(f"  Total runs: {total_runs}")
        print(f"  Results saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate image search system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full evaluation
  python scripts/evaluate.py

  # Custom output file
  python scripts/evaluate.py --output my_results.csv

  # Custom expansion factor
  python scripts/evaluate.py --expand 5

  # Evaluate only specific models
  python scripts/evaluate.py --models clip clip_rerank

  # Evaluate only specific difficulties
  python scripts/evaluate.py --difficulties eq mq
        """
    )

    parser.add_argument(
        "--output",
        default=str(EVALUATION_DIR / "results.csv"),
        help="Output CSV file path (default: data/evaluation/results.csv)"
    )

    parser.add_argument(
        "--expand",
        type=int,
        default=3,
        help="Expansion factor: fetch expand*k results before reranking (default: 3)"
    )

    parser.add_argument(
        "--models",
        nargs="+",
        choices=["clip", "clip_rerank"],
        help="Models to evaluate (default: all)"
    )

    parser.add_argument(
        "--difficulties",
        nargs="+",
        choices=["eq", "mq", "hq"],
        help="Query difficulties to evaluate (default: all)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Image Search Evaluation")
    print("=" * 80)
    print(f"Output: {args.output}")
    print(f"Expand factor: {args.expand}")
    print(f"Models: {args.models or 'all'}")
    print(f"Difficulties: {args.difficulties or 'all'}")
    print("=" * 80)
    print()

    run_evaluation(
        args.output,
        expand=args.expand,
        models=args.models,
        difficulties=args.difficulties
    )


if __name__ == "__main__":
    main()
