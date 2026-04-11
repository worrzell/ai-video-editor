import json
import logging
from pathlib import Path
from typing import List, Dict

import numpy as np

from backend.services.embedding import EmbeddingProvider
from backend.db.vector_store import VectorStore

logger = logging.getLogger(__name__)


def load_transcripts(transcripts_dir: Path) -> List[Dict]:
    """Load all transcript JSON files and flatten segments."""
    transcripts_dir = Path(transcripts_dir)
    if not transcripts_dir.exists():
        raise FileNotFoundError(f'Transcripts directory not found: {transcripts_dir}')
    
    transcript_files = sorted(transcripts_dir.glob('*.json'))
    if not transcript_files:
        raise ValueError(f'No transcript files found in {transcripts_dir}')
    
    segments = []
    for transcript_file in transcript_files:
        try:
            data = json.loads(transcript_file.read_text(encoding='utf-8'))
            clip_id = data.get('clip_id')
            for segment in data.get('segments', []):
                segments.append({
                    'clip_id': clip_id,
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                })
            logger.info(f'Loaded {len(data.get("segments", []))} segments from {clip_id}')
        except Exception as e:
            logger.error(f'Failed to load {transcript_file.name}: {e}')
    
    logger.info(f'Total segments loaded: {len(segments)}')
    return segments


def build_index(transcripts_dir: Path, output_dir: Path, embedding_model: str = 'all-MiniLM-L6-v2', batch_size: int = 32, use_multimodal: bool = True) -> tuple:
    """Build FAISS index from transcripts with optional multimodal embeddings."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info('Loading transcripts...')
    segments = load_transcripts(transcripts_dir)
    
    if not segments:
        raise ValueError('No segments to index')
    
    logger.info(f'Initializing embedding provider with model: {embedding_model}')
    embedding_provider = EmbeddingProvider(model_name=embedding_model)
    
    logger.info(f'Embedding {len(segments)} segments in batches of {batch_size}...')
    embeddings_list = []
    
    # Check if segments have visual embeddings
    has_visual = any('visual_embedding' in seg for seg in segments)
    
    if has_visual and use_multimodal:
        logger.info('Creating multimodal embeddings (text + visual)...')
        for i, seg in enumerate(segments):
            text = seg['text']
            visual_emb = seg.get('visual_embedding', None)
            
            # Create multimodal embedding
            multimodal_emb = embedding_provider.embed_multimodal(text, visual_emb, text_weight=0.6)
            embeddings_list.append(multimodal_emb)
            
            if (i + 1) % batch_size == 0:
                logger.info(f'Processed {i + 1}/{len(segments)} segments')
        
        embeddings = np.array(embeddings_list)
    else:
        if has_visual:
            logger.info('Visual embeddings found but multimodal mode disabled. Using text only.')
        
        # Text-only embeddings with batching
        texts = [seg['text'] for seg in segments]
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = embedding_provider.embed_texts(batch_texts)
            embeddings_list.append(batch_embeddings)
            logger.info(f'Embedded batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}')
        
        embeddings = np.vstack(embeddings_list)
    
    embedding_dim = embeddings.shape[1]
    logger.info(f'Embedding shape: {embeddings.shape}')
    
    logger.info('Building FAISS index...')
    vector_store = VectorStore(dimension=embedding_dim)
    vector_store.add(embeddings, segments)
    
    index_path = output_dir / 'embeddings.index'
    vector_store.save(index_path)
    logger.info(f'Index saved to {index_path}')
    
    return vector_store, segments


def load_index(output_dir: Path, embedding_dim: int = 384) -> VectorStore:
    """Load FAISS index from disk."""
    output_dir = Path(output_dir)
    index_path = output_dir / 'embeddings.index'
    
    if not index_path.exists():
        raise FileNotFoundError(f'Index not found at {index_path}')
    
    logger.info(f'Loading index from {index_path}')
    vector_store = VectorStore(dimension=embedding_dim)
    vector_store.load(index_path)
    logger.info(f'Index loaded with {len(vector_store.metadatas)} segments')
    
    return vector_store
