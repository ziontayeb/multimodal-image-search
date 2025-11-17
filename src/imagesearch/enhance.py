"""Query enhancement using Gemini for improved search results."""

from __future__ import annotations
import os
from typing import Dict

from .config import (
    GEMINI_MODEL,
    ENHANCE_SYSTEM_PROMPT,
    ENHANCE_FEW_SHOTS,
)


def _get_genai_client():
    """Initialize and return Gemini client."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. Please set it in your .env file."
        )
    return genai.Client(api_key=api_key)


def _build_contents(user_query: str) -> list:
    """
    Build conversation-style prompt with system instructions and few-shot examples.

    Args:
        user_query: User's search query

    Returns:
        List of message contents for Gemini
    """
    contents = [{"role": "user", "parts": [{"text": ENHANCE_SYSTEM_PROMPT}]}]

    # Add few-shot examples
    for q, a in ENHANCE_FEW_SHOTS:
        contents.append({"role": "user", "parts": [{"text": q}]})
        contents.append({"role": "model", "parts": [{"text": a}]})

    # Add actual query
    contents.append({"role": "user", "parts": [{"text": user_query}]})

    return contents


def enhance_query(query: str) -> str:
    """
    Enhance a user query into a descriptive sentence for better image search.

    The enhanced query starts with the original text and adds visual details
    that might appear in matching images.

    Args:
        query: Original user query

    Returns:
        Enhanced query with additional visual context
    """
    client = _get_genai_client()
    contents = _build_contents(query)

    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config={"temperature": 0.1}  # Low temperature for more literal output
    )

    text = (getattr(resp, "text", None) or "").strip()
    if not text:
        return query.strip()

    # Take only first line, remove quotes
    out = text.split("\n")[0].strip().strip(" \"'")

    # Ensure single sentence (remove trailing periods and extra sentences)
    if "." in out:
        parts = [p.strip() for p in out.split(".") if p.strip()]
        if parts:
            out = parts[0]

    return out


def load_enhanced_db(path: str = "data/queries/enhanced_queries.json") -> Dict[str, str]:
    """
    Load pre-computed enhanced queries from JSON file.

    Args:
        path: Path to enhanced queries JSON file

    Returns:
        Dictionary mapping query IDs to enhanced query text
    """
    import os
    import json

    if not os.path.exists(path):
        raise RuntimeError(
            f"{path} not found. Run scripts/prepare_cache.py first "
            "to generate enhanced queries."
        )
    with open(path, "r") as f:
        return json.load(f)


def get_used_query(
    query_id: str,
    original_text: str,
    enhanced: bool,
    enhanced_db: Dict[str, str]
) -> str:
    """
    Get the query to use for search (original or enhanced).

    This is used during evaluation to switch between modes without live API calls.

    Args:
        query_id: Query identifier
        original_text: Original query text
        enhanced: Whether to use enhanced query
        enhanced_db: Dictionary of enhanced queries

    Returns:
        Query text to use for search
    """
    if enhanced:
        return enhanced_db.get(query_id, original_text)
    return original_text