from typing import List, Dict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class EmbeddingProvider:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        if SentenceTransformer is None:
            raise ImportError('sentence-transformers is not installed. Install it to enable embeddings.')
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> 'np.ndarray':
        return self.model.encode(texts, normalize_embeddings=True)

    def embed_multimodal(self, text: str, visual_embedding: List[float] = None, text_weight: float = 0.7) -> 'np.ndarray':
        """Create a combined embedding from text and visual features.
        
        Args:
            text: Text content to embed
            visual_embedding: Optional visual embedding from CLIP
            text_weight: Weight for text embedding (0-1), visual gets (1-text_weight)
        
        Returns:
            Combined embedding vector
        """
        # Text embedding
        text_emb = self.embed_texts([text])[0]
        
        if visual_embedding is not None:
            visual_emb = np.array(visual_embedding)
            
            # Ensure same dimensions by padding if necessary
            if len(visual_emb) != len(text_emb):
                # Resize visual embedding to match text embedding size
                if len(visual_emb) < len(text_emb):
                    visual_emb = np.pad(visual_emb, (0, len(text_emb) - len(visual_emb)), mode='constant')
                else:
                    visual_emb = visual_emb[:len(text_emb)]
            
            # Normalize visual embedding
            visual_emb = visual_emb / (np.linalg.norm(visual_emb) + 1e-8)
            
            # Combine embeddings
            combined = text_weight * text_emb + (1 - text_weight) * visual_emb
            combined = combined / (np.linalg.norm(combined) + 1e-8)
            return combined
        
        return text_emb
