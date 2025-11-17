# Command Reference

Quick reference for all scripts.

## Scripts

| Script | Purpose |
|--------|---------|
| `manage_db.py` | Database management (add/delete/list/wipe) |
| `evaluate.py` | Run evaluation across all model configurations |

---

## Database Management (manage_db.py)

Quick reference for all database management commands.

## Basic Commands

| Command | Description |
|---------|-------------|
| `add` | Add images to the database |
| `delete` | Delete images from the database |
| `list` | List all images in the database |
| `info` | Show detailed info about an image |
| `stats` | Show database statistics |
| `export-captions` | Export captions to JSON |
| `wipe` | Wipe database (DESTRUCTIVE) |

## Add Images

```bash
# Single image with caption
python scripts/manage_db.py add --path /path/to/image.jpg --caption

# Directory with captions
python scripts/manage_db.py add --dir /path/to/images --caption

# Directory without captions (faster)
python scripts/manage_db.py add --dir /path/to/images

# Custom batch size
python scripts/manage_db.py add --dir /path/to/images --caption --batch 32
```

## Delete Images

```bash
# By file path
python scripts/manage_db.py delete --path /path/to/image.jpg

# By vector ID
python scripts/manage_db.py delete --id abc123def456
```

## View Data

```bash
# List images (summary)
python scripts/manage_db.py list

# List with full caption details
python scripts/manage_db.py list --captions

# Get info about specific image
python scripts/manage_db.py info --path /path/to/image.jpg
python scripts/manage_db.py info --id abc123def456

# Show database statistics
python scripts/manage_db.py stats
```

## Export

```bash
# Export to default location (data/captions/captions.json)
python scripts/manage_db.py export-captions

# Export to custom location
python scripts/manage_db.py export-captions --output my_captions.json
```

## Wipe Database

**WARNING: These commands permanently delete data!**

```bash
# Wipe EVERYTHING (Pinecone + captions + cache)
python scripts/manage_db.py wipe --all

# Wipe only Pinecone vectors (keep captions)
python scripts/manage_db.py wipe --pinecone

# Wipe only caption database and cache (keep Pinecone)
python scripts/manage_db.py wipe --captions
```

**Safety:** You must type `DELETE EVERYTHING` to confirm.

## Help

```bash
# General help
python scripts/manage_db.py --help

# Command-specific help
python scripts/manage_db.py add --help
python scripts/manage_db.py delete --help
python scripts/manage_db.py wipe --help
```

## Typical Workflows

### Initial Setup
```bash
# 1. Check current state
python scripts/manage_db.py stats

# 2. Add your images with captions
python scripts/manage_db.py add --dir ./my_images --caption

# 3. Verify
python scripts/manage_db.py list
```

### Start Over
```bash
# Wipe everything and start fresh
python scripts/manage_db.py wipe --all
python scripts/manage_db.py add --dir ./my_images --caption
```

### Regenerate Captions Only
```bash
# 1. Wipe captions but keep vectors
python scripts/manage_db.py wipe --captions

# 2. Re-add images with new captions
# (vectors will be updated, captions regenerated)
python scripts/manage_db.py add --dir ./my_images --caption
```

### Export for Evaluation
```bash
# Export captions before running evaluation
python scripts/manage_db.py export-captions --output evaluation_captions.json
```

## Output Files

| File/Directory | Purpose |
|---------------|---------|
| `data/captions/captions.json` | Main caption database |
| `cache/caption_cache/*.json` | Individual caption cache files |
| `cache/rp_512_to_384.npy` | Random projection matrix |

## Vector Information

- **Original CLIP dimension:** 512
- **Reduced dimension (RP):** 384 (configurable in `.env`)
- **Vector ID:** SHA-1 hash of file content
- **Metric:** Cosine similarity

## Caption Generation

When using `--caption`:
1. Image rescaled to 256px (longest edge)
2. Compressed to JPEG quality 50
3. Sent to Gemini API
4. Result cached in `cache/caption_cache/`
5. Result stored in `data/captions/captions.json`

---

## Evaluation (evaluate.py)

### Run Full Evaluation

```bash
# All models, all queries, all configurations
python scripts/evaluate.py

# Output: data/evaluation/results.csv
```

### Custom Options

```bash
# Custom output file
python scripts/evaluate.py --output my_results.csv

# Custom expansion factor (default: 3)
python scripts/evaluate.py --expand 5

# Specific models only
python scripts/evaluate.py --models clip
python scripts/evaluate.py --models clip_rerank

# Specific difficulties only
python scripts/evaluate.py --difficulties eq
python scripts/evaluate.py --difficulties eq mq

# Combine options
python scripts/evaluate.py --output test.csv --difficulties eq --expand 2
```

### What Gets Evaluated

| Configuration | Options |
|--------------|---------|
| **Models** | clip, clip_rerank_a1.0, clip_rerank_a0.6, clip_rerank_a0.4 |
| **Enhancement** | True, False |
| **Difficulties** | eq (easy), mq (medium), hq (hard) |
| **K values** | Varies by difficulty: eq=[15,8,1], mq=[10,5,1], hq=[5,3,1] |

**Total configurations**: 4 models × 2 enhancement × 3 difficulties × 5 queries × 3 k-values = **360 runs**

### Output Format

CSV with columns:
- `model` - Model name (e.g., "clip_rerank_a0.6")
- `enhancement` - True/False
- `difficulty` - eq, mq, or hq
- `query_id` - Query identifier (e.g., "eq1")
- `k` - Number of results
- `results` - JSON array of image names (e.g., `["eq1_1", "eq1_2", ...]`)

### Performance

- **First run**: ~45-60 minutes (building caches)
- **Subsequent runs**: ~10-15 minutes (using caches)
