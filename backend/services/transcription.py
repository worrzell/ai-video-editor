import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import whisper
except ImportError:
    whisper = None


def transcribe_clip(input_path: Path, model_name: str = 'small', language: str = None) -> Dict:
    """Transcribe a video clip using Whisper."""
    if whisper is None:
        raise ImportError('Whisper is not installed. Install openai-whisper to enable transcription.')

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f'Clip not found: {input_path}')

    try:
        logger.info(f'Loading Whisper model: {model_name}')
        model = whisper.load_model(model_name)
        
        logger.info(f'Transcribing {input_path.name}...')
        transcribe_args = {'language': language} if language else {}
        result = model.transcribe(str(input_path), **transcribe_args)
        
        language_detected = result.get('language', 'unknown')
        logger.info(f'Detected language: {language_detected}')
        
        segments = [
            {
                'start': float(segment['start']),
                'end': float(segment['end']),
                'text': segment['text'].strip(),
            }
            for segment in result.get('segments', [])
        ]
        
        transcript = {
            'clip_id': input_path.stem,
            'filename': input_path.name,
            'duration': float(result.get('duration', 0.0)),
            'language': language_detected,
            'segments': segments,
        }
        logger.info(f'Transcribed {len(segments)} segments from {input_path.name}')
        return transcript
    except Exception as e:
        logger.error(f'Transcription failed for {input_path.name}: {e}')
        raise


def save_transcript(output_dir: Path, transcript: Dict) -> Path:
    """Save transcript to JSON file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clip_id = transcript['clip_id']
    output_path = output_dir / f'{clip_id}.json'
    output_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.info(f'Saved transcript to {output_path}')
    return output_path


def add_visual_features_to_transcript(transcript: Dict, video_path: Path, include_visual: bool = True) -> Dict:
    """Add visual descriptions to transcript segments using CLIP."""
    if not include_visual:
        return transcript
    
    try:
        from backend.services.vision_extractor import VisionExtractor, extract_visual_features
        
        logger.info(f'Extracting visual features from {video_path.name}...')
        vision_extractor = VisionExtractor()
        enhanced_segments = extract_visual_features(video_path, transcript['segments'], vision_extractor)
        
        transcript['segments'] = enhanced_segments
        logger.info(f'Added visual features to {len(enhanced_segments)} segments')
    except Exception as e:
        logger.warning(f'Could not extract visual features: {e}. Continuing with audio only.')
    
    return transcript


def transcribe_clips(clips: List[Path], output_dir: Path, model_name: str = 'small', language: str = None, include_visual: bool = False) -> List[Dict]:
    """Transcribe multiple clips and save transcripts."""
    transcripts = []
    failed = []
    
    for clip_path in clips:
        try:
            transcript = transcribe_clip(clip_path, model_name=model_name, language=language)
            
            # Optionally add visual features
            if include_visual:
                transcript = add_visual_features_to_transcript(transcript, clip_path, include_visual=True)
            
            transcripts.append(transcript)
            save_transcript(output_dir, transcript)
        except Exception as e:
            logger.error(f'Failed to transcribe {clip_path.name}: {e}')
            failed.append((clip_path.name, str(e)))
    
    if failed:
        logger.warning(f'{len(failed)} clip(s) failed to transcribe')
    
    return transcripts
