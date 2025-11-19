"""Re-index all images in web/uploads/ to update paths to relative format."""

from __future__ import annotations
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.imagesearch.index import upsert_dir


def main():
    """Re-index all images in web/uploads/ directory."""
    uploads_dir = Path(__file__).parent.parent / "web" / "uploads"

    if not uploads_dir.exists():
        print(f"Error: Directory {uploads_dir} does not exist")
        return

    print(f"Re-indexing images from: {uploads_dir}")
    print("This will update existing vectors with new relative paths...")
    print()

    total = upsert_dir(str(uploads_dir), batch_size=32)

    print()
    print(f"✓ Successfully re-indexed {total} images")
    print("All paths are now stored as relative paths (e.g., 'web/uploads/image.jpg')")


if __name__ == "__main__":
    main()
