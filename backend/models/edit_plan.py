from pydantic import BaseModel
from typing import List

class ClipSegment(BaseModel):
    clip_id: str
    start: float
    end: float
    reason: str = ""

class StyleConfig(BaseModel):
    pace: str = "normal"
    captions: bool = False
    aspect_ratio: str = "16:9"

class EditPlan(BaseModel):
    timeline: List[ClipSegment]
    style: StyleConfig