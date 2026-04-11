import logging
from pathlib import Path
from typing import List, Dict

from backend.db.vector_store import VectorStore
from backend.services.embedding import EmbeddingProvider

logger = logging.getLogger(__name__)


def retrieve_segments(prompt: str, vector_store: VectorStore, embedding_provider: EmbeddingProvider, top_k: int = 5) -> List[Dict]:
    """Retrieve top-k segments matching the prompt."""
    logger.info(f'Retrieving top-{top_k} segments for prompt: "{prompt}"')
    
    query_embedding = embedding_provider.embed_texts([prompt])
    results = vector_store.query(query_embedding, top_k=top_k)
    
    logger.info(f'Retrieved {len(results)} segments')
    for i, result in enumerate(results, 1):
        text_preview = result.get("text", "")[:50]
        visual_preview = ""
        if 'visual_description' in result:
            visual_preview = f" | visual: {result['visual_description'][:40]}"
        logger.info(f'  {i}. {result["clip_id"]} ({result["start"]:.1f}s-{result["end"]:.1f}s): {text_preview}...{visual_preview} (score: {result["score"]:.4f})')
    
    return results


def retrieve_segments_from_all_clips(vector_store: VectorStore, segments_per_clip: int = 3) -> List[Dict]:
    """Retrieve segments evenly distributed across all clips."""
    logger.info(f'Retrieving {segments_per_clip} segments from each clip')
    
    # Get all segments from the vector store
    all_segments = vector_store.get_all_segments()
    
    # Group by clip_id
    clips_segments = {}
    for segment in all_segments:
        clip_id = segment['clip_id']
        if clip_id not in clips_segments:
            clips_segments[clip_id] = []
        clips_segments[clip_id].append(segment)
    
    # Sample segments_per_clip from each clip
    results = []
    for clip_id, segments in clips_segments.items():
        # Sort by start time and take first segments_per_clip
        segments_sorted = sorted(segments, key=lambda x: x['start'])
        selected = segments_sorted[:segments_per_clip]
        results.extend(selected)
        logger.info(f'  Selected {len(selected)} segments from {clip_id}')
    
    logger.info(f'Total segments retrieved: {len(results)} from {len(clips_segments)} clips')
    return results

