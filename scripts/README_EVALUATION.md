# Evaluation Script

Comprehensive evaluation system for the image search project.

## Overview

The evaluation script (`evaluate.py`) runs systematic tests across different model configurations, query difficulties, and k values. It outputs results to CSV for analysis.

## What Gets Evaluated

### Models
1. **clip** - Basic CLIP search (no reranking)
2. **clip_rerank_a1.0** - Caption reranking with alpha=1.0 (pure caption similarity)
3. **clip_rerank_a0.6** - Caption reranking with alpha=0.6 (60% caption, 40% CLIP)
4. **clip_rerank_a0.4** - Caption reranking with alpha=0.4 (40% caption, 60% CLIP)

### Enhancement Settings
- **True** - Query enhanced by Gemini before search
- **False** - Original query used as-is

### Query Difficulties
From `data/queries/queries.json`:

| Difficulty | Code | K Values | Example Queries |
|------------|------|----------|-----------------|
| Easy | eq | [15, 8, 1] | "Sunset on the beach", "Red car" |
| Medium | mq | [10, 5, 1] | "A man sitting on a boat", "Study to exams" |
| Hard | hq | [5, 3, 1] | "Photos from Burning Man", "Feeling lonely" |

### Total Configurations

For each combination of:
- Model (4 options)
- Enhancement (2 options: True/False)
- Difficulty (3 levels: eq, mq, hq)
- Query (5 queries per difficulty)
- K value (3 values per difficulty)

**Total runs**: 4 × 2 × 3 × 5 × 3 = **360 search operations**

## How It Works

### 1. Query Enhancement (if enabled)
- Checks cache in `data/queries/enhanced_cache.json`
- If not cached, calls Gemini to enhance query
- Saves to cache for future use

### 2. Search Execution
- Fetches `expand × k` results from Pinecone (default expand=3)
- If reranking:
  - Gets captions (from cache or generates with Gemini)
  - Computes caption similarity with query
  - Blends scores: `final = (1-alpha) × clip_score + alpha × caption_sim`
  - Takes top k from reranked results
- If no reranking:
  - Just takes top k from initial results

### 3. Result Extraction
- Extracts image names from paths
- Example: `"data/example_images/eq1_1.jpg"` → `"eq1_1"`
- Image name contains query ID for true positive matching

### 4. CSV Output

Columns:
- **model**: Model name (e.g., "clip", "clip_rerank_a0.6")
- **enhancement**: True/False
- **difficulty**: eq, mq, or hq
- **query_id**: Query identifier (e.g., "eq1")
- **k**: Number of results requested
- **results**: JSON array of image names (e.g., `["eq1_1", "eq1_2", "mq2_5"]`)

Example row:
```csv
model,enhancement,difficulty,query_id,k,results
clip_rerank_a0.6,True,eq,eq1,15,"[""eq1_1"",""eq1_2"",""eq1_3"",...]"
```

## Usage

### Run Full Evaluation

```bash
python scripts/evaluate.py
```

This runs all 360 configurations and saves to `data/evaluation/results.csv`

### Custom Output File

```bash
python scripts/evaluate.py --output my_results.csv
```

### Custom Expansion Factor

```bash
python scripts/evaluate.py --expand 5
```

Fetches 5×k results before reranking (default is 3×k)

### Evaluate Specific Models

```bash
# Only CLIP, no reranking
python scripts/evaluate.py --models clip

# Only reranking models
python scripts/evaluate.py --models clip_rerank
```

### Evaluate Specific Difficulties

```bash
# Only easy queries
python scripts/evaluate.py --difficulties eq

# Only easy and medium
python scripts/evaluate.py --difficulties eq mq
```

### Combine Options

```bash
python scripts/evaluate.py \
  --output quick_test.csv \
  --models clip \
  --difficulties eq \
  --expand 2
```

## Caching

### Enhanced Queries
- Location: `data/queries/enhanced_cache.json`
- Format: `{"eq1": "enhanced query text", ...}`
- Automatically saved when generated

### Captions
- Location: `cache/caption_cache/{vector_id}.json`
- Generated on-demand during reranking
- Reused across evaluation runs

This caching significantly speeds up repeated evaluations.

## Output Analysis

### True Positive Detection

A result is a true positive if the image name contains the query ID:

```python
query_id = "eq1"
results = ["eq1_1", "eq1_2", "mq2_3", "eq1_5"]

true_positives = [r for r in results if query_id in r]
# → ["eq1_1", "eq1_2", "eq1_5"]
```

### Metrics You Can Compute

From the CSV, you can calculate:

1. **Precision@k**: `true_positives / k`
2. **Recall@k**: `true_positives / total_relevant_images`
3. **Mean Average Precision (MAP)**
4. **NDCG (Normalized Discounted Cumulative Gain)**

## Example Output

```csv
model,enhancement,difficulty,query_id,k,results
clip,False,eq,eq1,15,"[""eq1_1"",""eq1_2"",""mq3_4"",""eq1_3"",...]"
clip,True,eq,eq1,15,"[""eq1_1"",""eq1_5"",""eq1_2"",""hq2_1"",...]"
clip_rerank_a1.0,False,eq,eq1,15,"[""eq1_1"",""eq1_2"",""eq1_3"",...]"
clip_rerank_a0.6,False,eq,eq1,15,"[""eq1_2"",""eq1_1"",""eq1_4"",...]"
...
```

## Performance Estimation

**Approximate runtime** (depends on caching):

- First run (no cache): ~45-60 minutes
  - 360 searches × ~5-10 seconds each
  - Includes Gemini API calls for enhancement and captions

- Subsequent runs (with cache): ~10-15 minutes
  - No Gemini calls needed
  - Only CLIP embedding and search

## Tips

1. **Run once with all data** to populate caches
2. **Subset runs for testing** using `--models` and `--difficulties` flags
3. **Check cache** before running: `ls cache/caption_cache/ | wc -l`
4. **Monitor progress** - Script prints each configuration as it runs

## Troubleshooting

**Missing captions**
- Script auto-generates them during evaluation
- Check `GEMINI_API_KEY` in `.env`

**Slow performance**
- First run is slow (building caches)
- Subsequent runs much faster
- Reduce `--expand` value to speed up

**Out of memory**
- Reduce `--expand` value
- Run subsets with `--difficulties eq` or similar

## Next Steps

After evaluation:
1. Load CSV in Python/R/Excel
2. Calculate metrics (precision, recall, MAP)
3. Compare models and configurations
4. Visualize results (bar charts, heatmaps)
5. Statistical significance testing
