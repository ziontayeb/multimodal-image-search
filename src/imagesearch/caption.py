"""Image captioning using Gemini vision models."""

from __future__ import annotations
import base64
import json
import time
from io import BytesIO
from pathlib import Path
from typing import Tuple, Dict, Optional

from PIL import Image

from .config import GEMINI_MODEL, CAPTION_PROMPT, CAPTION_CACHE_DIR


_genai = None


def _get_client():
    """Lazy initialization of Gemini client."""
    global _genai
    if _genai is None:
        import os
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not found. Please set it in your .env file."
            )
        _genai = genai.Client(api_key=api_key)
    return _genai


def _prep_image(
    path: str,
    max_long_edge: int = 256,
    jpeg_quality: int = 50
) -> Tuple[str, str, Dict]:
    """
    Prepare image for Gemini API by resizing and converting to base64.

    Args:
        path: Path to the image file
        max_long_edge: Maximum size for the longest edge
        jpeg_quality: JPEG compression quality (1-100)

    Returns:
        Tuple of (mime_type, base64_data, stats)
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size

    # Resize if needed
    scale = min(1.0, max_long_edge / max(w, h))
    if scale < 1.0:
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # Convert to JPEG and base64
    buf = BytesIO()
    img.save(
        buf,
        format="JPEG",
        quality=jpeg_quality,
        optimize=True,
        progressive=True,
        subsampling=2
    )
    data = buf.getvalue()
    b64_data = base64.b64encode(data).decode("utf-8")

    stats = {
        "orig_size": (w, h),
        "new_size": img.size,
        "jpeg_bytes": len(data)
    }

    return "image/jpeg", b64_data, stats


def _extract_text(resp) -> str:
    """Extract text from Gemini response object."""
    if hasattr(resp, "text") and resp.text:
        return resp.text.strip()

    for c in getattr(resp, "candidates", []) or []:
        content = getattr(c, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None)
        if not parts:
            continue

        texts = [
            getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
            for p in parts
        ]
        texts = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
        if texts:
            return " ".join(texts)

    return str(resp)


def _clean_caption_text(raw: str) -> str:
    """
    Clean Gemini's caption output to remove verbose prefixes.

    Args:
        raw: Raw caption text from Gemini

    Returns:
        Cleaned caption text
    """
    if not raw:
        return ""

    text = raw.strip()

    # Remove content after first colon
    if ":" in text:
        text = text.split(":", 1)[1]

    # Remove line breaks and excessive spaces
    text = " ".join(text.split())

    # Remove common prefixes
    prefixes = [
        "Here is", "Here's", "Certainly", "This image", "The image shows"
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip(" ,.-").strip()
            break

    return text


# Cache functions
def _cache_path(key: str) -> Path:
    """Get cache file path for a given key."""
    return CAPTION_CACHE_DIR / f"{key}.json"


def get_cached(key: str, ttl_days: int = 365) -> Optional[str]:
    """
    Retrieve cached caption by key.

    Args:
        key: Cache key (typically file hash)
        ttl_days: Time-to-live in days

    Returns:
        Cached caption or None if not found/expired
    """
    p = _cache_path(key)
    if not p.exists():
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("ts", 0) > ttl_days * 86400:
            return None
        return data.get("caption")
    except Exception:
        return None


def put_cached(key: str, caption: str):
    """
    Store caption in cache.

    Args:
        key: Cache key (typically file hash)
        caption: Caption text to cache
    """
    p = _cache_path(key)
    data = {"caption": caption, "ts": time.time()}
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# Main caption function
def describe_image(path: str) -> Tuple[str, Dict]:
    """
    Generate a caption for an image using Gemini.

    Args:
        path: Path to the image file

    Returns:
        Tuple of (caption, stats) where stats includes token counts
    """
    client = _get_client()
    mime, b64, stats = _prep_image(path)

    contents = [{
        "role": "user",
        "parts": [
            {"inline_data": {"mime_type": mime, "data": b64}},
            {"text": CAPTION_PROMPT}
        ]
    }]

    # Count input tokens
    try:
        ct = client.models.count_tokens(model=GEMINI_MODEL, contents=contents)
        input_tokens = getattr(ct, "total_tokens", None)
    except Exception:
        input_tokens = None

    # Generate caption
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
    raw_caption = _extract_text(resp)
    caption = _clean_caption_text(raw_caption)

    # Get output tokens
    um = getattr(resp, "usage_metadata", None)
    output_tokens = getattr(um, "output_tokens", None) if um else None

    return caption, {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        **stats
    }


# Utility functions for working with caption databases
def _strip_path(path: str) -> str:
    """
    Extract filename stem from path.

    Example: "example_images/ed1_1.jpg" -> "ed1_1"
    """
    import os
    base = os.path.basename(path)
    stem, _ = os.path.splitext(base)
    return stem


def load_caption_db(path: str = "data/captions/captions.json") -> Dict[str, str]:
    """
    Load pre-generated captions from JSON file.

    Args:
        path: Path to captions JSON file

    Returns:
        Dictionary mapping filename stems to captions
    """
    import os
    if not os.path.exists(path):
        raise RuntimeError(
            f"{path} not found. Run scripts/prepare_cache.py first "
            "to generate captions."
        )
    with open(path, "r") as f:
        return json.load(f)


def offline_caption_getter(caption_db: Dict[str, str]):
    """
    Create a caption getter function for offline use (no Gemini calls).

    Args:
        caption_db: Dictionary of filename stems to captions

    Returns:
        Function that takes a full path and returns cached caption
    """
    def _getter(path: str) -> str:
        stem = _strip_path(path)
        return caption_db.get(stem, "")

    return _getter