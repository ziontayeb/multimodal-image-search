"""Configuration settings for the image search system."""

from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Directory paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
DATA_DIR = PROJECT_ROOT / "data"

# Cache directories
CAPTION_CACHE_DIR = CACHE_DIR / "caption_cache"
QUERY_CACHE_DIR = CACHE_DIR / "query_cache"
CAPTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
QUERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Random Projection settings
REDUCE_DIM = int(os.getenv("REDUCE_DIM", "384"))
RP_MATRIX_PATH = str(CACHE_DIR / f"rp_512_to_{REDUCE_DIM}.npy")

# Pinecone index settings
INDEX_NAME = os.getenv("INDEX_NAME", f"img-search-clip-rp-{REDUCE_DIM}")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

# Model configurations
CLIP_MODEL = os.getenv("CLIP_MODEL", "sentence-transformers/clip-ViT-B-32")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Caption generation prompt
CAPTION_PROMPT = (
    "Describe this image in 2–4 sentences as a single paragraph. "
    "Use only visible facts: the main subject and any actions or poses; "
    "notable objects or clothing; a few key colors; background elements; "
    "and the lighting or atmosphere. Avoid speculation and brand names."
)

# Query enhancement system prompt
ENHANCE_SYSTEM_PROMPT = (
    "You rewrite short user queries into one clear, descriptive sentence for an image search engine.\n"
    "\n"
    "Your output must:\n"
    "- Keep the user's exact wording at the start.\n"
    "- Continue the same sentence with a short phrase such as "
    "'the image might show ...' or 'the image might include ...'.\n"
    "- In that clause, describe only what could visually appear in a photo "
    "that matches the query: objects, subjects, environments, or settings directly implied by it.\n"
    "\n"
    "Strict rules:\n"
    "- Do NOT invent events, actions, emotions, relationships, props, or scenery not clearly implied.\n"
    "- Do NOT add story, mood, time of day, or creative embellishment unless already explicit.\n"
    "- Use neutral, factual language.\n"
    "- If the query already looks like a complete photo caption, simply return it as-is.\n"
    "- If the query is abstract (e.g. emotions, ideas), you may briefly ground it "
    "in a neutral, plausible visual form (e.g. 'a single person sitting alone').\n"
    "- Output exactly ONE sentence, no bullet points, no multiple sentences, no quotes.\n"
    "- Stay concise (under ~40 tokens).\n"
)

# Query enhancement few-shot examples
ENHANCE_FEW_SHOTS = [
    (
        "a person reading",
        "a person reading, the image might include an open book and hands holding the pages"
    ),
    (
        "mountain landscape",
        "a mountain landscape, the image might include rocky peaks and a clear sky"
    ),
    (
        "city skyline",
        "a city skyline, the image might include tall modern buildings and an urban horizon"
    ),
    (
        "fruit on a table",
        "fruit on a table, the image might include apples and oranges arranged on a wooden surface"
    ),
    (
        "feeling lonely",
        "feeling lonely, the image might include a single person sitting alone on a bench in an open space"
    ),
]