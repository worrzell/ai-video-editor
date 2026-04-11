import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None


class VectorStore:
    def __init__(self, dimension: int):
        if faiss is None:
            raise ImportError('faiss is not installed. Install it to enable the vector store.')
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadatas: List[Dict[str, Any]] = []

    def add(self, embeddings: 'np.ndarray', metadatas: List[Dict[str, Any]]):
        if embeddings.shape[1] != self.dimension:
            raise ValueError('Embedding dimension mismatch.')
        self.index.add(embeddings.astype('float32'))
        self.metadatas.extend(metadatas)

    def query(self, query_vector: 'np.ndarray', top_k: int = 5) -> List[Dict[str, Any]]:
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        distances, indexes = self.index.search(query_vector.astype('float32'), top_k)
        results = []
        for dist, idx in zip(distances[0], indexes[0]):
            if idx < 0 or idx >= len(self.metadatas):
                continue
            metadata = self.metadatas[idx].copy()
            metadata['score'] = float(dist)
            results.append(metadata)
        return results

    def get_all_segments(self) -> List[Dict[str, Any]]:
        """Return all segments in the store."""
        return self.metadatas.copy()

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))
        metadata_path = path.with_suffix('.meta.json')
        metadata_path.write_text(json.dumps(self.metadatas, indent=2), encoding='utf-8')

    def load(self, path: Path):
        self.index = faiss.read_index(str(path))
        metadata_path = path.with_suffix('.meta.json')
        self.metadatas = json.loads(metadata_path.read_text(encoding='utf-8'))
