# Implementation Spec: Phase 2 - Embeddings & Retrieval

## Objective
Implement the embeddings and retrieval pipeline to vectorize transcript segments and enable semantic search based on user prompts.

## Scope

### Embedding Service
- **Input:** Transcript segments from Phase 1 output
- **Process:**
  1. Load embedding model (sentence-transformers, default: all-MiniLM-L6-v2)
  2. Convert text segments to dense vectors (384 dimensions)
  3. Normalize embeddings for cosine similarity
- **Output:** Dense vectors ready for FAISS indexing
- **Location:** `backend/services/embedding.py`

### Vector Store (FAISS)
- **Input:** Embeddings and metadata
- **Process:**
  1. Build FAISS index from segment embeddings
  2. Store metadata (clip_id, start, end, text, score) alongside embeddings
  3. Support save/load operations for persistence
- **Output:** Queryable FAISS index with metadata
- **Location:** `backend/db/vector_store.py`

### Retrieval Service
- **Input:** User prompt string
- **Process:**
  1. Convert prompt to embedding using same model as Phase 2
  2. Query FAISS index with top-k retrieval (default k=5)
  3. Return ranked segments with similarity scores
- **Output:** List of relevant segments sorted by relevance
- **Location:** `backend/services/retrieval.py`

### Indexing Pipeline
- **Input:** All transcripts from Phase 1
- **Process:**
  1. Load all transcript JSON files
  2. Flatten segments and create metadata records
  3. Generate embeddings in batches
  4. Build and save FAISS index
- **Output:** `data/embeddings.index` and `data/embeddings.meta.json`
- **Location:** New service `backend/services/indexing.py`

### CLI Commands (Phase 2)
- `python backend/main.py index` — builds FAISS index from transcripts
- `python backend/main.py search "prompt"` — searches index and returns top segments

### Data Files
- `data/embeddings.index` — FAISS index file
- `data/embeddings.meta.json` — Segment metadata and embeddings metadata
- `data/retrieval_cache.json` (optional) — cache recent searches

## Dependencies
- sentence-transformers (embeddings)
- faiss-cpu (vector search)
- numpy (vector operations)

## Success Criteria
1. `index` command successfully builds FAISS index from all transcripts
2. `search` command retrieves top-k relevant segments with scores
3. Retrieval quality is high (relevant segments appear at top positions)
4. Index can be saved and loaded without data loss
5. Batch processing handles large transcript sets efficiently
6. Error handling for missing transcripts or corrupted files

## Notes
- Embedding model can be made configurable via CLI option
- Top-k parameter defaults to 5 but can be adjusted
- FAISS index uses L2 distance (Euclidean); cosine similarity can be computed from L2 distances
- Embeddings are cached to avoid recomputation on repeated queries
