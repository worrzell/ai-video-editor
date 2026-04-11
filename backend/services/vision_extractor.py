import logging
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    import clip
    import torch
    from PIL import Image
except ImportError:
    cv2 = None
    clip = None
    torch = None


class VisionExtractor:
    """Extract visual features and descriptions from video frames using CLIP."""

    def __init__(self, model_name: str = "ViT-B/32", device: str = None):
        if clip is None or torch is None:
            raise ImportError('CLIP and torch are required for vision extraction. Install openai-clip and torch.')
        
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.device = device
        logger.info(f'Loading CLIP model: {model_name} on device: {device}')
        self.model, self.preprocess = clip.load(model_name, device=device)
        self.model.eval()
        logger.info(f'CLIP model loaded on {device}')

    def extract_frames(self, video_path: Path, start_time: float, end_time: float, num_frames: int = 2) -> List[np.ndarray]:
        """Extract frames from a video segment."""
        if cv2 is None:
            raise ImportError('opencv-python is required for frame extraction.')
        
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f'Video file not found: {video_path}')
        
        try:
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps == 0:
                logger.warning(f'Could not determine FPS for {video_path.name}')
                return []
            
            # Calculate frame numbers
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            frames = []
            frame_positions = np.linspace(start_frame, end_frame, num_frames, dtype=int)
            
            for frame_num in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)
            
            cap.release()
            logger.info(f'Extracted {len(frames)} frames from {video_path.name} ({start_time:.1f}s-{end_time:.1f}s)')
            return frames
        except Exception as e:
            logger.error(f'Failed to extract frames from {video_path.name}: {e}')
            return []

    def describe_frames(self, frames: List[np.ndarray]) -> str:
        """Generate text descriptions of video frames using CLIP."""
        if not frames:
            return "No visual content"
        
        try:
            # Define visual concepts to detect
            concepts = [
                "landscape", "mountain", "water", "ocean", "lake", "river",
                "forest", "trees", "sky", "clouds", "sunset", "sunrise",
                "drone flying", "aerial view", "wide angle", "close-up",
                "fast movement", "slow movement", "rotating", "panning",
                "person", "animal", "building", "urban", "city",
                "bright", "dark", "daytime", "nighttime",
                "natural scenery", "artificial scenery"
            ]
            
            descriptions = []
            
            for i, frame_array in enumerate(frames):
                # Convert numpy array to PIL Image
                frame_pil = Image.fromarray(frame_array)
                
                # Process frame with CLIP preprocessing
                image_tensor = self.preprocess(frame_pil).unsqueeze(0).to(self.device)
                
                # Encode concepts
                concept_texts = [f"a video showing {concept}" for concept in concepts]
                text_inputs = clip.tokenize(concept_texts).to(self.device)
                
                # Get CLIP embeddings
                with torch.no_grad():
                    image_features = self.model.encode_image(image_tensor)
                    text_features = self.model.encode_text(text_inputs)
                    
                    # Normalize
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                    text_features /= text_features.norm(dim=-1, keepdim=True)
                    
                    # Calculate similarity
                    similarities = (image_features @ text_features.T).cpu().numpy()
                    
                # Get top concepts
                top_indices = similarities[0].argsort()[-5:][::-1]
                top_concepts = [concepts[idx] for idx in top_indices]
                top_scores = similarities[0][top_indices]
                
                # Build description
                description_parts = []
                for concept, score in zip(top_concepts, top_scores):
                    if score > 0.2:  # Only include high confidence
                        description_parts.append(concept)
                
                description = ", ".join(description_parts) if description_parts else "visual content"
                descriptions.append(description)
                logger.info(f'Frame {i+1}: {description}')
            
            # Combine all frame descriptions
            combined_description = " | ".join(descriptions)
            return combined_description
        except Exception as e:
            logger.error(f'Failed to describe frames: {e}')
            return "visual content"

    def extract_visual_embedding(self, frames: List[np.ndarray]) -> np.ndarray:
        """Extract visual embeddings from frames using CLIP."""
        if not frames:
            return np.zeros(512)  # Return zero vector if no frames
        
        try:
            embeddings = []
            
            for frame_array in frames:
                frame_pil = Image.fromarray(frame_array)
                image_tensor = self.preprocess(frame_pil).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    image_features = self.model.encode_image(image_tensor)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                    embeddings.append(image_features.cpu().numpy())
            
            # Average embeddings from all frames
            combined_embedding = np.mean(embeddings, axis=0)[0]
            return combined_embedding
        except Exception as e:
            logger.error(f'Failed to extract visual embedding: {e}')
            return np.zeros(512)


def extract_visual_features(video_path: Path, segments: List[Dict], vision_extractor: VisionExtractor = None) -> List[Dict]:
    """Extract visual features for all segments in a video."""
    if vision_extractor is None:
        vision_extractor = VisionExtractor()
    
    enhanced_segments = []
    
    for segment in segments:
        try:
            # Extract frames from this segment
            frames = vision_extractor.extract_frames(
                video_path,
                segment['start'],
                segment['end'],
                num_frames=2
            )
            
            # Generate visual description
            visual_description = vision_extractor.describe_frames(frames)
            
            # Extract visual embedding
            visual_embedding = vision_extractor.extract_visual_embedding(frames)
            
            # Enhance segment with visual information
            enhanced_segment = segment.copy()
            enhanced_segment['visual_description'] = visual_description
            enhanced_segment['visual_embedding'] = visual_embedding.tolist()
            enhanced_segments.append(enhanced_segment)
            
            logger.info(f'Enhanced segment with visual features: {visual_description[:50]}...')
        except Exception as e:
            logger.error(f'Failed to extract visual features for segment: {e}')
            # Fall back to original segment without visual info
            enhanced_segments.append(segment)
    
    return enhanced_segments
