"""Command-line interface for the image search system."""

from __future__ import annotations
import argparse
from typing import Callable

from . import index
from .embeddings import file_id
from .caption import describe_image, get_cached, put_cached
from .rerank import rerank_by_caption
from .enhance import enhance_query


class SearchMode:
    """Search mode constants."""
    CLIP = "clip"
    CLIP_RERANK = "clip_rerank"


def _get_caption_cached(path: str) -> str:
    """
    Get caption for an image, using cache when available.

    Args:
        path: Path to the image file

    Returns:
        Image caption
    """
    key = file_id(path)
    cap = get_cached(key)
    if cap:
        return cap

    cap, _ = describe_image(path)
    put_cached(key, cap)
    return cap


def cmd_insert(args) -> None:
    """
    Insert command: Add images to the index.

    Args:
        args: Parsed command-line arguments
    """
    if args.path:
        vid = index.upsert_one(args.path)
        print(f"Upserted {vid} → {args.path}")
    elif args.dir:
        n = index.upsert_dir(args.dir, batch_size=args.batch)
        print(f"Upserted {n} images from {args.dir}")
    else:
        print("Error: Provide --path or --dir")


def cmd_search(args) -> None:
    """
    Search command: Search for images matching a query.

    Args:
        args: Parsed command-line arguments
    """
    # 1) Optionally enhance the query
    user_query = args.query
    used_query = enhance_query(user_query) if args.enhance else user_query

    if args.enhance:
        print(f"Original query: {user_query}")
        print(f"Enhanced query: {used_query}\n")

    # 2) Fetch expand*K results using CLIP
    fetch_k = max(1, args.top_k * args.expand)
    matches = index.search(used_query, fetch_k)

    if not matches:
        print("No results found.")
        return

    # 3) Display results based on mode
    if args.mode == SearchMode.CLIP:
        print(f"Top {min(args.top_k, len(matches))} results (CLIP only):\n")
        for i, m in enumerate(matches[:args.top_k], 1):
            score = m['score']
            path = m['metadata'].get('path', '')
            vid = m['id']
            print(f"{i:>2}. score={score:.3f}  id={vid}")
            print(f"    {path}\n")
        return

    if args.mode == SearchMode.CLIP_RERANK:
        print(f"Reranking top {fetch_k} results by caption similarity...\n")
        out = rerank_by_caption(
            used_query,
            matches,
            _get_caption_cached,
            alpha=args.alpha,
            use_blend=True
        )
        out = out[:args.top_k]

        print(f"Top {len(out)} results (CLIP + Caption Reranking):\n")
        for i, r in enumerate(out, 1):
            print(f"{i:>2}. final={r['final_score']:.3f}  "
                  f"caption_sim={r['caption_sim']:.3f}  "
                  f"orig={r['orig_score']:.3f}")
            print(f"    {r['path']}")
            print(f"    Caption: {r['caption']}\n")
        return

    print(f"Unknown mode: {args.mode}. Use 'clip' or 'clip_rerank'")


def cmd_stats(args) -> None:
    """
    Stats command: Display index statistics.

    Args:
        args: Parsed command-line arguments
    """
    stats = index.stats()
    print("Index Statistics:")
    print(f"  Name: {index._name}")
    print(f"  Total vectors: {stats.get('total_vector_count', 0)}")
    print(f"  Dimension: {stats.get('dimension', 'N/A')}")
    print(f"  Namespaces: {list(stats.get('namespaces', {}).keys())}")


def cmd_wipe(args) -> None:
    """
    Wipe command: Delete all vectors from the index.

    Args:
        args: Parsed command-line arguments
    """
    confirm = input(
        "WARNING: This will delete ALL vectors from the index. "
        "Type 'yes' to confirm: "
    )
    if confirm.lower() == "yes":
        index.wipe()
    else:
        print("Aborted.")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Image Search System with CLIP and Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Insert single image
  %(prog)s insert --path /path/to/image.jpg

  # Insert all images in directory
  %(prog)s insert --dir /path/to/images --batch 32

  # Basic CLIP search
  %(prog)s search --query "sunset on beach" --top_k 10

  # Search with caption reranking
  %(prog)s search --query "sunset on beach" --mode clip_rerank --top_k 10

  # Search with query enhancement
  %(prog)s search --query "sunset" --enhance --mode clip_rerank
        """
    )

    subparsers = parser.add_subparsers(dest="cmd", help="Available commands")

    # Insert command
    p_insert = subparsers.add_parser(
        "insert",
        help="Insert images into the index"
    )
    p_insert.add_argument(
        "--path",
        help="Path to single image file"
    )
    p_insert.add_argument(
        "--dir",
        help="Path to directory containing images"
    )
    p_insert.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Batch size for processing multiple images (default: 16)"
    )
    p_insert.set_defaults(func=cmd_insert)

    # Search command
    p_search = subparsers.add_parser(
        "search",
        help="Search for images by text query"
    )
    p_search.add_argument(
        "--query",
        required=True,
        help="Text search query"
    )
    p_search.add_argument(
        "--top_k",
        type=int,
        default=10,
        help="Number of results to return (default: 10)"
    )
    p_search.add_argument(
        "--expand",
        type=int,
        default=3,
        help="Fetch factor: retrieve expand*top_k before reranking (default: 3)"
    )
    p_search.add_argument(
        "--mode",
        choices=["clip", "clip_rerank"],
        default="clip",
        help="Search mode: 'clip' (fast) or 'clip_rerank' (slower, more accurate)"
    )
    p_search.add_argument(
        "--alpha",
        type=float,
        default=0.6,
        help="Blend weight for caption similarity in reranking (0.0-1.0, default: 0.6)"
    )
    p_search.add_argument(
        "--enhance",
        action="store_true",
        help="Use Gemini to enhance query before search"
    )
    p_search.set_defaults(func=cmd_search)

    # Stats command
    p_stats = subparsers.add_parser(
        "stats",
        help="Show index statistics"
    )
    p_stats.set_defaults(func=cmd_stats)

    # Wipe command
    p_wipe = subparsers.add_parser(
        "wipe",
        help="Delete all vectors from the index"
    )
    p_wipe.set_defaults(func=cmd_wipe)

    # Parse and execute
    args = parser.parse_args()
    if not getattr(args, "cmd", None):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
