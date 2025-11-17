# Database Management Script

This script (`manage_db.py`) provides comprehensive utilities for managing your Pinecone vector database and caption storage.

## Features

- **Add/Insert photos** to Pinecone vector database
- **Delete photos** by path or vector ID
- **View vector dimensions** and embeddings
- **Generate captions** using Gemini (with automatic image rescaling to reduce tokens)
- **Cache caption results** for faster access
- **Store captions in JSON** for later evaluation and access
- **List and inspect** all indexed images

## Prerequisites

Make sure you have set up your environment variables in `.env`:
```
PINECONE_API_KEY=your_pinecone_key
GEMINI_API_KEY=your_gemini_key
```

## Usage

### Add Images

**Add a single image with caption generation:**
```bash
python scripts/manage_db.py add --path /path/to/image.jpg --caption
```

**Add a directory of images with captions:**
```bash
python scripts/manage_db.py add --dir /path/to/images --caption
```

**Add images WITHOUT caption generation:**
```bash
python scripts/manage_db.py add --dir /path/to/images
```

### Delete Images

**Delete by file path:**
```bash
python scripts/manage_db.py delete --path /path/to/image.jpg
```

**Delete by vector ID:**
```bash
python scripts/manage_db.py delete --id abc123def456
```

### View Database Contents

**List all images:**
```bash
python scripts/manage_db.py list
```

**List with full caption details:**
```bash
python scripts/manage_db.py list --captions
```

**Get detailed info about a specific image:**
```bash
python scripts/manage_db.py info --path /path/to/image.jpg
# or
python scripts/manage_db.py info --id abc123def456
```

### Statistics

**View database statistics:**
```bash
python scripts/manage_db.py stats
```

This shows:
- Pinecone index statistics (total vectors, dimension)
- Caption database statistics (total captions, sources)
- Namespace information

### Export Captions

**Export captions to JSON:**
```bash
python scripts/manage_db.py export-captions --output my_captions.json
```

If no output path is specified, saves to `data/captions/captions.json`

### Wipe Database

**Wipe entire database (Pinecone vectors + caption database + cache):**
```bash
python scripts/manage_db.py wipe --all
```

**Wipe only Pinecone vectors (keep captions):**
```bash
python scripts/manage_db.py wipe --pinecone
```

**Wipe only caption database and cache (keep Pinecone vectors):**
```bash
python scripts/manage_db.py wipe --captions
```

**Safety features:**
- You must type `DELETE EVERYTHING` to confirm
- Shows exactly what will be deleted before confirmation
- The action cannot be undone

**Use cases:**
- `--all`: Start completely fresh with new images
- `--pinecone`: Keep captions but rebuild vector index
- `--captions`: Keep vectors but regenerate all captions

## How Caption Generation Works

When you use the `--caption` flag:

1. **Image Rescaling**: Images are automatically resized (default max edge: 256px) and compressed (JPEG quality: 50) to reduce token usage
2. **Gemini API Call**: The rescaled image is sent to Gemini for caption generation
3. **Caching**:
   - Generated captions are cached in `cache/caption_cache/{vector_id}.json`
   - If you request a caption for the same image again, it uses the cache instead of calling Gemini
4. **JSON Storage**: Captions are also stored in `data/captions/captions.json` for easy access during evaluation

## Caption Database Structure

The captions are stored in JSON format:

```json
{
  "abc123def456": {
    "path": "/path/to/image.jpg",
    "caption": "A sunset over a calm ocean with orange and pink hues in the sky...",
    "source": "generated",
    "stats": {
      "orig_size": [3024, 4032],
      "new_size": [192, 256],
      "jpeg_bytes": 12345,
      "input_tokens": 500,
      "output_tokens": 50
    }
  }
}
```

- **Key**: SHA-1 hash of the image file (vector ID)
- **path**: Original file path
- **caption**: Generated caption text
- **source**: Either "generated" (from Gemini) or "cache" (from previous generation)
- **stats**: Image rescaling and token usage statistics

## Vector Dimensions

The system uses Random Projection for dimensionality reduction:
- Original CLIP embeddings: 512 dimensions
- Reduced dimensions: 384 (default, configurable via REDUCE_DIM in .env)

## For Evaluation

All captions are stored in `data/captions/captions.json` which you can use for your evaluation process:

```python
import json

# Load all captions
with open('data/captions/captions.json', 'r') as f:
    captions = json.load(f)

# Access caption by vector ID
vector_id = "abc123def456"
caption = captions[vector_id]['caption']
```

## Tips

1. **Start without captions** for faster indexing, then add captions later if needed
2. **Use cache** - if you re-run caption generation, it will use cached results
3. **Check stats** regularly to monitor your database size and caption coverage
4. **Export captions** before running evaluation to ensure you have a snapshot

## Troubleshooting

**Error: GEMINI_API_KEY not found**
- Make sure you have set `GEMINI_API_KEY` in your `.env` file

**Error: PINECONE_API_KEY not found**
- Make sure you have set `PINECONE_API_KEY` in your `.env` file

**No images found**
- Check that your image directory contains files with extensions: .jpg, .jpeg, .png (case-insensitive)