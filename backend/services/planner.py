import json
import logging
import os
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from backend.models.edit_plan import ClipSegment, EditPlan, StyleConfig

logger = logging.getLogger(__name__)


def build_planner_prompt(prompt: str, retrieved_segments: List[Dict]) -> str:
    """Build a structured prompt for the Gemini LLM planner, including visual information if available."""
    
    # Check if visual information is available
    has_visual = any('visual_description' in item for item in retrieved_segments)
    
    if has_visual:
        # Include both text and visual information
        segment_text = '\n'.join(
            f"- clip_id: {item['clip_id']}, start: {item['start']:.2f}s, end: {item['end']:.2f}s, text: {item['text'][:60]}, visual: {item.get('visual_description', 'N/A')[:60]}"
            for item in retrieved_segments
        )
    else:
        # Text only
        segment_text = '\n'.join(
            f"- clip_id: {item['clip_id']}, start: {item['start']:.2f}s, end: {item['end']:.2f}s, text: {item['text'][:80]}"
            for item in retrieved_segments
        )
    
    schema = {
        "timeline": [
            {"clip_id": "string", "start": "float", "end": "float", "reason": "string (optional)"}
        ],
        "style": {
            "pace": "slow|normal|fast",
            "captions": "boolean",
            "aspect_ratio": "16:9|9:16|1:1"
        }
    }
    
    visual_note = " including visual content from the video frames" if has_visual else ""
    
    prompt_text = f"""You are a professional video editor. Generate a strict JSON edit plan based on the user's request{visual_note}.

USER REQUEST: {prompt}

AVAILABLE SEGMENTS:
{segment_text}

CONSTRAINTS:
1. Only use clip_ids from the list above
2. Use exact start/end times from the segments
3. Do not hallucinate timestamps or clip_ids
4. Create a logical, engaging sequence of segments
5. Try to include segments from as many different clips as possible
6. Keep the total video length reasonable (under 60 seconds)
7. Consider both audio (text) and visual content when making selections
8. Output ONLY valid JSON matching the schema below

JSON SCHEMA:
{json.dumps(schema, indent=2)}

RESPONSE (JSON ONLY):"""
    
    return prompt_text


def call_gemini_api(prompt_text: str, api_key: Optional[str] = None, model_name: Optional[str] = None) -> Dict:
    """Invoke Google Gemini API directly with JSON response formatting."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured in backend environment.")

    model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    clean_model = model.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={key}"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt_text}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates returned from Gemini: {data}")
        text_content = candidates[0]["content"]["parts"][0]["text"]
        return json.loads(text_content)


def plan_edit(
    prompt: str,
    retrieved_segments: List[Dict],
    model_name: Optional[str] = None,
    max_retries: int = 2
) -> EditPlan:
    """Generate an edit plan using Google Gemini Cloud API."""
    if not retrieved_segments:
        logger.warning('No segments provided for planning. Creating empty plan.')
        return create_fallback_plan([])
    
    planner_prompt = build_planner_prompt(prompt, retrieved_segments)
    model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    
    for attempt in range(max_retries):
        try:
            logger.info(f'Calling Gemini model {model} (attempt {attempt + 1}/{max_retries})...')
            plan_data = call_gemini_api(planner_prompt, model_name=model)
            
            # Validate plan structure and clip timestamps
            plan = validate_plan(plan_data, retrieved_segments)
            logger.info(f'Generated valid Gemini plan with {len(plan.timeline)} segments')
            return plan
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f'Gemini HTTP error (attempt {attempt + 1}): {e.code} {error_body}')
            continue
        except Exception as e:
            logger.error(f'Gemini planner error (attempt {attempt + 1}): {e}')
            continue
    
    logger.warning('Gemini planner failed. Using fallback plan.')
    return create_fallback_plan(retrieved_segments)


def validate_plan(plan_data: Dict, retrieved_segments: List[Dict]) -> EditPlan:
    """Validate and construct an EditPlan from LLM output."""
    valid_clip_ids = {seg['clip_id'] for seg in retrieved_segments}
    
    # Extract timeline
    timeline_data = plan_data.get('timeline', [])
    if not timeline_data:
        raise ValueError('Empty timeline in plan')
    
    valid_timeline = []
    for item in timeline_data[:20]:  # Enforce max 20 clips
        clip_id = item.get('clip_id')
        start = float(item.get('start', 0))
        end = float(item.get('end', 0))
        reason = item.get('reason', '')
        
        # Validate clip_id exists
        if clip_id not in valid_clip_ids:
            logger.warning(f'Skipping invalid clip_id: {clip_id}')
            continue
        
        # Find matching segment and validate timestamps
        matching_segment = None
        tolerance = 0.1
        for seg in retrieved_segments:
            if (seg['clip_id'] == clip_id and 
                abs(seg['start'] - start) <= tolerance and 
                abs(seg['end'] - end) <= tolerance):
                matching_segment = seg
                break
        
        if not matching_segment:
            logger.warning(f'Timestamps out of bounds for {clip_id}: {start}-{end}')
            # Try to find any segment with this clip_id as fallback
            matching_segments = [s for s in retrieved_segments if s['clip_id'] == clip_id]
            if matching_segments:
                matching_segment = matching_segments[0]
                start, end = matching_segment['start'], matching_segment['end']
        
        if matching_segment:
            valid_timeline.append(ClipSegment(
                clip_id=clip_id,
                start=start,
                end=end,
                reason=reason
            ))
    
    if not valid_timeline:
        raise ValueError('No valid segments in timeline after validation')
    
    # Extract style
    style_data = plan_data.get('style', {})
    style = StyleConfig(
        pace=style_data.get('pace', 'normal'),
        captions=style_data.get('captions', False),
        aspect_ratio=style_data.get('aspect_ratio', '16:9')
    )
    
    return EditPlan(timeline=valid_timeline, style=style)


def create_fallback_plan(retrieved_segments: List[Dict]) -> EditPlan:
    """Create a simple sequential plan from top segments."""
    logger.info('Creating fallback plan from top segments')
    timeline = []
    
    # Use top segments in order
    for seg in retrieved_segments[:10]:
        timeline.append(ClipSegment(
            clip_id=seg['clip_id'],
            start=seg['start'],
            end=seg['end'],
            reason='Fallback sequential selection'
        ))
    
    style = StyleConfig(pace='normal', captions=False, aspect_ratio='16:9')
    return EditPlan(timeline=timeline, style=style)
