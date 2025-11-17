# Image Search System

A semantic image search system powered by CLIP embeddings, Pinecone vector database, and Gemini AI for enhanced search accuracy.

## Features

- **CLIP-based Image Search**: Fast semantic search using CLIP vision-language embeddings (ViT-B/32 base model)
- **Dimensionality Reduction**: Random projection for efficient storage (512d → 384d)
- **Caption-based Reranking**: Improved accuracy using Gemini-generated image captions
- **Query Enhancement**: Automatic query expansion with Gemini for better results
- **Pinecone Vector Database**: Scalable vector storage and similarity search
- **Two Search Modes**:
  - **CLIP mode**: Fast retrieval using image-text similarity
  - **CLIP + Rerank mode**: Two-stage retrieval for higher accuracy
- **Web Interface**: Modern, locally-hosted web UI with:
  - Natural language search with real-time results
  - Fixed-size collage layout (8 images, no scrolling)
  - Drag-and-drop image upload
  - Search history and settings management
  - Runs on port 5001 (avoiding macOS AirPlay conflicts)

## Architecture

```
┌─────────────┐
│  Text Query │
└──────┬──────┘
       │
       ├─────────────────────────────┐
       │                             │
       v (optional)                  │
┌──────────────┐                     │
│Query Enhancement│                  │
│   (Gemini)   │                     │
└──────┬───────┘                     │
       │                             │
       v                             v
┌──────────────┐              ┌──────────────┐
│ CLIP Text    │              │ CLIP Image   │
│ Embedding    │              │ Embeddings   │
│  (512d)      │              │   (512d)     │
└──────┬───────┘              └──────┬───────┘
       │                             │
       v                             v
┌──────────────┐              ┌──────────────┐
│   Random     │              │   Random     │
│ Projection   │              │ Projection   │
│  (→ 384d)    │              │  (→ 384d)    │
└──────┬───────┘              └──────┬───────┘
       │                             │
       └──────────┬───────────────────┘
                  v
           ┌──────────────┐
           │  Pinecone    │
           │Vector Search │
           │  (Top K×N)   │
           └──────┬───────┘
                  │
                  v (optional)
           ┌──────────────┐
           │Caption-based │
           │  Reranking   │
           │  (Top K)     │
           └──────┬───────┘
                  │
                  v
           ┌──────────────┐
           │   Results    │
           └──────────────┘
```

## Installation

### Prerequisites

- Python 3.8+
- API keys for:
  - [Pinecone](https://www.pinecone.io/) (for vector database)
  - [Google Gemini](https://ai.google.dev/) (for captions and query enhancement)

### Setup

1. **Clone or create the project:**
   ```bash
   cd image-search-clean
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```env
   # Required API Keys
   PINECONE_API_KEY=your_pinecone_api_key
   GEMINI_API_KEY=your_gemini_api_key

   # Optional Configuration
   REDUCE_DIM=384
   INDEX_NAME=img-search-clip-rp-384
   PINECONE_CLOUD=aws
   PINECONE_REGION=us-east-1
   CLIP_MODEL=sentence-transformers/clip-ViT-B-32
   GEMINI_MODEL=gemini-2.0-flash
   ```

4. **Install the package:**
   ```bash
   pip install -e .
   ```

## Usage

### Web Interface (Recommended)

The easiest way to use the system is through the web interface:

```bash
cd web
python app.py
```

Then open `http://localhost:5001` in your browser.

**Features**:
- Natural language search with visual results
- Fixed-size collage showing up to 8 images
- Drag-and-drop image upload
- Search history in browser
- Settings management

See [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) for complete documentation.

### Command Line Interface

For programmatic access, the system provides a CLI:

```bash
python -m imagesearch.cli <command> [options]
```

### Inserting Images

**Insert a single image:**
```bash
python -m imagesearch.cli insert --path /path/to/image.jpg
```

**Insert all images from a directory:**
```bash
python -m imagesearch.cli insert --dir /path/to/images --batch 32
```

### Searching

**Basic CLIP search (fast):**
```bash
python -m imagesearch.cli search --query "sunset on the beach" --top_k 10
```

**CLIP + Caption reranking (more accurate):**
```bash
python -m imagesearch.cli search \
  --query "sunset on the beach" \
  --mode clip_rerank \
  --top_k 10 \
  --expand 3 \
  --alpha 0.6
```

**With query enhancement:**
```bash
python -m imagesearch.cli search \
  --query "sunset" \
  --enhance \
  --mode clip_rerank \
  --top_k 10
```

### Index Management

**View index statistics:**
```bash
python -m imagesearch.cli stats
```

**Delete all vectors (careful!):**
```bash
python -m imagesearch.cli wipe
```

## Configuration Options

### Search Parameters

- `--query`: Text search query (required)
- `--top_k`: Number of results to return (default: 10)
- `--expand`: Fetch factor for reranking (default: 3)
  - Retrieves `expand × top_k` results before reranking
  - Higher values = more accurate but slower
- `--mode`: Search mode
  - `clip`: Fast CLIP-only search
  - `clip_rerank`: Two-stage search with caption reranking
- `--alpha`: Reranking blend weight (default: 0.6)
  - 0.0 = use only original CLIP scores
  - 1.0 = use only caption similarity
  - 0.6 = balanced blend
- `--enhance`: Enable query enhancement with Gemini

### Environment Variables

See `.env.example` for full configuration options.

## Python API

You can also use the package programmatically:

```python
from imagesearch import (
    upsert_one,
    upsert_dir,
    search,
    rerank_by_caption,
    enhance_query,
)

# Insert images
upsert_dir("my_images/", batch_size=16)

# Basic search
results = search("sunset on beach", top_k=10)

# Enhanced search with reranking
from imagesearch.caption import load_caption_db, offline_caption_getter

enhanced = enhance_query("sunset")
results = search(enhanced, top_k=30)

caption_db = load_caption_db("data/captions/captions.json")
get_caption = offline_caption_getter(caption_db)
reranked = rerank_by_caption(enhanced, results, get_caption, alpha=0.6)
```

## Cache Preparation

For faster evaluation/search, pre-generate captions and enhanced queries:

```bash
python scripts/prepare_cache.py
```

This will:
1. Generate captions for all images in `example_images/`
2. Generate enhanced versions of all queries in `data/queries/queries.json`
3. Cache results to avoid repeated API calls

## Project Structure

```
image-search-clean/
├── README.md                 # This file
├── WEB_UI_GUIDE.md          # Web interface quick start
├── PROJECT_SUMMARY.md       # Project cleanup summary
├── requirements.txt          # Python dependencies
├── setup.py                  # Package installation
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
│
├── src/
│   └── imagesearch/         # Main package
│       ├── __init__.py      # Package exports
│       ├── config.py        # Configuration
│       ├── embeddings.py    # CLIP embeddings + random projection
│       ├── index.py         # Pinecone index management
│       ├── caption.py       # Gemini image captioning
│       ├── enhance.py       # Gemini query enhancement
│       ├── rerank.py        # Caption-based reranking
│       └── cli.py           # Command-line interface
│
├── web/                     # Web interface
│   ├── app.py              # Flask API server
│   ├── templates/          # HTML templates
│   ├── static/             # CSS/JS assets
│   └── uploads/            # Uploaded images
│
├── scripts/
│   ├── prepare_cache.py    # Pre-generate captions/queries
│   ├── manage_db.py        # Database management
│   └── evaluate.py         # Evaluation scripts
│
├── data/
│   ├── captions/            # Cached captions
│   ├── queries/             # Query specifications
│   └── evaluation/          # Evaluation results
│
├── cache/
│   ├── caption_cache/       # Gemini caption cache
│   ├── query_cache/         # Gemini query cache
│   └── rp_*.npy            # Random projection matrix
│
├── notebooks/               # Jupyter notebooks for analysis
└── tests/                   # Unit tests
```

## How It Works

### 1. Image Indexing

1. Images are loaded and encoded using CLIP (ViT-B/32 base model)
2. 512-dimensional embeddings are normalized to unit vectors
3. Embeddings are projected to 384 dimensions using random projection
4. Projected vectors are normalized again to unit vectors
5. Vectors are stored in Pinecone with metadata (file path)

### 2. Search (CLIP mode)

1. Query text is encoded with CLIP
2. Query vector is projected to 384 dimensions
3. Pinecone returns top-K most similar images

### 3. Search (CLIP + Rerank mode)

1. Retrieve top K×N results using CLIP (fast retrieval)
2. Generate captions for retrieved images using Gemini
3. Compute caption-query similarity in full CLIP text space (512d)
4. Blend original and caption scores
5. Return top-K reranked results

### 4. Query Enhancement

Gemini rewrites short queries into descriptive sentences:
- Input: "sunset"
- Output: "sunset, the image might include a colorful sky, sun near horizon, and silhouettes"

## Performance Tips

1. **Use CLIP mode for speed**: ~10x faster than reranking
2. **Adjust expand factor**: Higher = more accurate but slower
3. **Pre-generate captions**: Run `prepare_cache.py` before batch evaluation
4. **Tune alpha**: 0.6 works well, but experiment for your dataset

## API Rate Limits

The system includes rate limiting for Gemini API (free tier):
- Max 60 calls per batch
- 1-2 second delay between calls
- 10 second delay between batches

Adjust in `scripts/prepare_cache.py` if needed.

## Troubleshooting

**"PINECONE_API_KEY not found"**
- Make sure you created `.env` from `.env.example`
- Check that API key is correctly set

**"Index not found"**
- The index will be created automatically on first run
- Check Pinecone dashboard to verify

**"Rate limit exceeded"**
- Increase delays in `prepare_cache.py`
- Wait a few minutes and retry

**Out of memory**
- Reduce `--batch` size when inserting images
- Reduce `--expand` factor when searching

**Web UI: "Port 5001 already in use"** (macOS)
- Port changed from 5000 to 5001 to avoid AirPlay Receiver conflicts
- If 5001 is also taken, edit `web/app.py` line 321 to use a different port
- Or disable AirPlay Receiver: System Preferences → General → AirDrop & Handoff

**Web UI: Images not displaying**
- Fixed in latest version with improved path handling
- Images are served from absolute paths or `web/uploads/`
- Check browser console (F12) for specific errors

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [CLIP](https://github.com/openai/CLIP) by OpenAI
- [Sentence Transformers](https://www.sbert.net/)
- [Pinecone](https://www.pinecone.io/)
- [Google Gemini](https://ai.google.dev/)