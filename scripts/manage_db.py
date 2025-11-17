#!/usr/bin/env python3
"""
Database Management Script for Image Search Project

This script provides utilities to:
- Add/insert/delete photos from Pinecone vector database
- View embedded vector dimensions
- Generate captions using Gemini (with image rescaling)
- Cache and store captions in JSON for later access
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from imagesearch import index
from imagesearch.embeddings import file_id, encode_image
from imagesearch.caption import describe_image, get_cached, put_cached
from imagesearch.config import DATA_DIR, REDUCE_DIM


# Caption database path
CAPTIONS_DB_PATH = DATA_DIR / "captions" / "captions.json"


def load_captions_db() -> Dict[str, Dict]:
    """Load the captions database from JSON."""
    CAPTIONS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CAPTIONS_DB_PATH.exists():
        with open(CAPTIONS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_captions_db(db: Dict[str, Dict]) -> None:
    """Save the captions database to JSON."""
    CAPTIONS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CAPTIONS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print(f"Caption database saved to: {CAPTIONS_DB_PATH}")


def get_or_generate_caption(image_path: str, use_gemini: bool = True) -> Optional[Dict]:
    """
    Get caption for an image, either from cache or by generating new one.

    Args:
        image_path: Path to the image file
        use_gemini: If True, generate caption using Gemini if not cached

    Returns:
        Dictionary with caption and metadata, or None if not available
    """
    vid = file_id(image_path)

    # Try cache first
    cached_caption = get_cached(vid)
    if cached_caption:
        return {
            "caption": cached_caption,
            "source": "cache",
            "vector_id": vid
        }

    # Generate new caption if enabled
    if use_gemini:
        print(f"  Generating caption with Gemini for: {image_path}")
        try:
            caption, stats = describe_image(image_path)

            # Cache the result
            put_cached(vid, caption)

            return {
                "caption": caption,
                "source": "generated",
                "vector_id": vid,
                "stats": stats
            }
        except Exception as e:
            print(f"  Error generating caption: {e}")
            return None

    return None


def cmd_add(args) -> None:
    """Add images to the database with optional captioning."""
    caption_enabled = args.caption

    if args.path:
        # Add single image
        print(f"Adding image: {args.path}")

        # Generate/get caption if enabled
        caption_data = None
        if caption_enabled:
            caption_data = get_or_generate_caption(args.path, use_gemini=True)

        # Insert into Pinecone
        vid = index.upsert_one(args.path)
        print(f"  Vector ID: {vid}")
        print(f"  Path: {args.path}")
        print(f"  Vector dimension: {REDUCE_DIM}")

        # Save caption to database
        if caption_data:
            db = load_captions_db()
            db[vid] = {
                "path": args.path,
                "caption": caption_data["caption"],
                "source": caption_data["source"]
            }
            if "stats" in caption_data:
                db[vid]["stats"] = caption_data["stats"]
            save_captions_db(db)
            print(f"  Caption: {caption_data['caption']}")

    elif args.dir:
        # Add directory of images
        print(f"Adding images from directory: {args.dir}")
        print(f"Caption generation: {'enabled' if caption_enabled else 'disabled'}")
        print(f"Batch size: {args.batch}\n")

        # Get list of image files
        from glob import glob
        patterns = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
        files = sorted({
            p for pat in patterns
            for p in glob(os.path.join(args.dir, pat))
        })

        if not files:
            print(f"No image files found in {args.dir}")
            return

        print(f"Found {len(files)} images")

        # Load caption database
        caption_db = load_captions_db() if caption_enabled else None

        # Process in batches
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processing: {file_path}")

            # Generate/get caption if enabled
            caption_data = None
            if caption_enabled:
                caption_data = get_or_generate_caption(file_path, use_gemini=True)

            # Insert into Pinecone
            vid = index.upsert_one(file_path)
            print(f"  Vector ID: {vid}")

            # Save caption to database
            if caption_data and caption_db is not None:
                caption_db[vid] = {
                    "path": file_path,
                    "caption": caption_data["caption"],
                    "source": caption_data["source"]
                }
                if "stats" in caption_data:
                    caption_db[vid]["stats"] = caption_data["stats"]
                print(f"  Caption: {caption_data['caption']}")

        # Save all captions at once
        if caption_enabled and caption_db:
            save_captions_db(caption_db)

        print(f"\nTotal images added: {len(files)}")
    else:
        print("Error: Provide --path or --dir")


def cmd_delete(args) -> None:
    """Delete images from the database."""
    if args.path:
        print(f"Deleting image: {args.path}")
        vid = file_id(args.path)

        # Delete from Pinecone
        index.delete_by_path(args.path)
        print(f"  Deleted vector: {vid}")

        # Remove from caption database
        db = load_captions_db()
        if vid in db:
            del db[vid]
            save_captions_db(db)
            print(f"  Removed from caption database")

    elif args.id:
        print(f"Deleting by vector ID: {args.id}")

        # Delete from Pinecone by ID
        index.index.delete(ids=[args.id])
        print(f"  Deleted vector: {args.id}")

        # Remove from caption database
        db = load_captions_db()
        if args.id in db:
            del db[args.id]
            save_captions_db(db)
            print(f"  Removed from caption database")
    else:
        print("Error: Provide --path or --id")


def cmd_list(args) -> None:
    """List all images in the database."""
    # Get Pinecone stats
    stats = index.stats()
    total = stats.get('total_vector_count', 0)

    print(f"Total vectors in Pinecone: {total}")
    print(f"Vector dimension: {REDUCE_DIM}")
    print()

    # Load caption database
    db = load_captions_db()

    if args.captions:
        print(f"Images with captions ({len(db)}):")
        print("=" * 80)
        for vid, data in db.items():
            print(f"\nVector ID: {vid}")
            print(f"Path: {data.get('path', 'N/A')}")
            print(f"Caption: {data.get('caption', 'N/A')}")
            print(f"Source: {data.get('source', 'N/A')}")
            if 'stats' in data:
                stats_info = data['stats']
                print(f"Stats: {stats_info}")
    else:
        print(f"Images with captions: {len(db)}")
        print("Use --captions flag to see full details")


def cmd_info(args) -> None:
    """Show detailed information about a specific image."""
    if args.path:
        vid = file_id(args.path)
    elif args.id:
        vid = args.id
    else:
        print("Error: Provide --path or --id")
        return

    print(f"Image Information")
    print("=" * 80)
    print(f"Vector ID: {vid}")

    # Check if in caption database
    db = load_captions_db()
    if vid in db:
        data = db[vid]
        print(f"Path: {data.get('path', 'N/A')}")
        print(f"Caption: {data.get('caption', 'N/A')}")
        print(f"Source: {data.get('source', 'N/A')}")
        if 'stats' in data:
            print(f"\nCaption Generation Stats:")
            for key, value in data['stats'].items():
                print(f"  {key}: {value}")

    # Show vector dimension
    print(f"\nVector dimension: {REDUCE_DIM}")

    # Try to get embedding if path provided
    if args.path and os.path.exists(args.path):
        vec = encode_image(args.path)
        print(f"Embedding shape: {vec.shape}")
        print(f"Embedding sample (first 10 values): {vec[:10]}")


def cmd_stats(args) -> None:
    """Show database statistics."""
    # Pinecone stats
    stats = index.stats()

    print("Pinecone Index Statistics")
    print("=" * 80)
    print(f"Index name: {index.INDEX_NAME}")
    print(f"Total vectors: {stats.get('total_vector_count', 0)}")
    print(f"Dimension: {stats.get('dimension', 'N/A')}")
    print(f"Configured dimension (RP): {REDUCE_DIM}")

    namespaces = stats.get('namespaces', {})
    if namespaces:
        print(f"\nNamespaces:")
        for ns, ns_stats in namespaces.items():
            print(f"  {ns}: {ns_stats.get('vector_count', 0)} vectors")

    # Caption database stats
    db = load_captions_db()
    print(f"\nCaption Database Statistics")
    print("=" * 80)
    print(f"Total captions stored: {len(db)}")
    print(f"Database location: {CAPTIONS_DB_PATH}")

    # Count caption sources
    sources = {}
    for data in db.values():
        source = data.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1

    if sources:
        print(f"\nCaption sources:")
        for source, count in sources.items():
            print(f"  {source}: {count}")


def cmd_export_captions(args) -> None:
    """Export captions to a JSON file."""
    db = load_captions_db()

    output_path = args.output or CAPTIONS_DB_PATH

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(db)} captions to: {output_path}")


def cmd_generate_captions(args) -> None:
    """Generate captions for all images in Pinecone that don't have captions yet."""
    # Get all images from Pinecone
    stats = index.stats()
    total = stats.get('total_vector_count', 0)

    print(f"Total vectors in Pinecone: {total}")

    # This is a simplified version - in practice, you'd need to fetch all vectors
    # from Pinecone which requires pagination through the index
    print("\nNote: This command generates captions for images specified by path.")
    print("To generate captions for all indexed images, use the --dir option with 'add' command.")


def cmd_wipe(args) -> None:
    """Wipe the entire database (Pinecone vectors and/or caption database)."""
    wipe_pinecone = args.all or args.pinecone
    wipe_captions = args.all or args.captions

    if not wipe_pinecone and not wipe_captions:
        print("Error: Specify --all, --pinecone, or --captions")
        return

    # Show what will be wiped
    print("\nWARNING: You are about to delete:")
    if wipe_pinecone:
        stats = index.stats()
        total = stats.get('total_vector_count', 0)
        print(f"  - ALL {total} vectors from Pinecone index '{index.INDEX_NAME}'")
    if wipe_captions:
        db = load_captions_db()
        print(f"  - ALL {len(db)} captions from caption database")

    print("\nThis action CANNOT be undone!")

    # Confirmation
    confirm = input("\nType 'DELETE EVERYTHING' to confirm: ")

    if confirm != "DELETE EVERYTHING":
        print("Aborted. No data was deleted.")
        return

    # Wipe Pinecone
    if wipe_pinecone:
        print("\nWiping Pinecone index...")
        index.wipe()
        print("  ✓ Pinecone index wiped")

    # Wipe caption database
    if wipe_captions:
        print("\nWiping caption database...")
        if CAPTIONS_DB_PATH.exists():
            CAPTIONS_DB_PATH.unlink()
            print(f"  ✓ Deleted {CAPTIONS_DB_PATH}")

        # Also clear caption cache
        from imagesearch.config import CAPTION_CACHE_DIR
        if CAPTION_CACHE_DIR.exists():
            import shutil
            cache_files = list(CAPTION_CACHE_DIR.glob("*.json"))
            for f in cache_files:
                f.unlink()
            print(f"  ✓ Cleared {len(cache_files)} cached captions")

    print("\n✓ Database wipe completed successfully!")
    print("\nYou can now start fresh by adding new images.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database Management for Image Search System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add single image with caption
  python manage_db.py add --path /path/to/image.jpg --caption

  # Add directory of images with captions
  python manage_db.py add --dir /path/to/images --caption

  # Add images without captions
  python manage_db.py add --dir /path/to/images

  # Delete image by path
  python manage_db.py delete --path /path/to/image.jpg

  # Delete image by vector ID
  python manage_db.py delete --id abc123def456

  # List all images
  python manage_db.py list

  # List with captions
  python manage_db.py list --captions

  # Show info about specific image
  python manage_db.py info --path /path/to/image.jpg

  # Show database statistics
  python manage_db.py stats

  # Export captions
  python manage_db.py export-captions --output my_captions.json

  # Wipe entire database (Pinecone + captions)
  python manage_db.py wipe --all

  # Wipe only Pinecone vectors
  python manage_db.py wipe --pinecone

  # Wipe only caption database
  python manage_db.py wipe --captions
        """
    )

    subparsers = parser.add_subparsers(dest="cmd", help="Available commands")

    # Add command
    p_add = subparsers.add_parser("add", help="Add images to the database")
    p_add.add_argument("--path", help="Path to single image file")
    p_add.add_argument("--dir", help="Path to directory containing images")
    p_add.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    p_add.add_argument("--caption", action="store_true", help="Generate captions using Gemini")
    p_add.set_defaults(func=cmd_add)

    # Delete command
    p_delete = subparsers.add_parser("delete", help="Delete images from the database")
    p_delete.add_argument("--path", help="Path to image file")
    p_delete.add_argument("--id", help="Vector ID")
    p_delete.set_defaults(func=cmd_delete)

    # List command
    p_list = subparsers.add_parser("list", help="List all images in the database")
    p_list.add_argument("--captions", action="store_true", help="Show full caption details")
    p_list.set_defaults(func=cmd_list)

    # Info command
    p_info = subparsers.add_parser("info", help="Show detailed info about an image")
    p_info.add_argument("--path", help="Path to image file")
    p_info.add_argument("--id", help="Vector ID")
    p_info.set_defaults(func=cmd_info)

    # Stats command
    p_stats = subparsers.add_parser("stats", help="Show database statistics")
    p_stats.set_defaults(func=cmd_stats)

    # Export captions command
    p_export = subparsers.add_parser("export-captions", help="Export captions to JSON")
    p_export.add_argument("--output", help="Output JSON file path")
    p_export.set_defaults(func=cmd_export_captions)

    # Wipe command
    p_wipe = subparsers.add_parser("wipe", help="Wipe database (DESTRUCTIVE)")
    wipe_group = p_wipe.add_mutually_exclusive_group(required=True)
    wipe_group.add_argument("--all", action="store_true", help="Wipe everything (Pinecone + captions)")
    wipe_group.add_argument("--pinecone", action="store_true", help="Wipe only Pinecone vectors")
    wipe_group.add_argument("--captions", action="store_true", help="Wipe only caption database")
    p_wipe.set_defaults(func=cmd_wipe)

    # Parse and execute
    args = parser.parse_args()
    if not getattr(args, "cmd", None):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()