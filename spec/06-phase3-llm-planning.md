# Implementation Spec: Phase 3 - LLM Planning

## Objective
Implement the LLM planning service to generate structured JSON edit plans from user prompts and retrieved segments using a local LLM via Ollama.

## Scope

### LLM Planner Service
- **Input:**
  - User prompt (natural language edit request)
  - Top-k retrieved segments from Phase 2 retrieval
- **Process:**
  1. Build a structured prompt with retrieved segments and schema
  2. Call Ollama LLM with strict JSON output formatting
  3. Parse and validate the returned JSON edit plan
  4. Enforce constraints: only use provided clip_ids, include valid timestamps
- **Output:** Validated `EditPlan` object with timeline and style config
- **Location:** `backend/services/planner.py` (already stubbed, needs full implementation)

### EditPlan Schema (Pydantic)
- **Timeline:** List of ClipSegment objects
  - `clip_id`: string (must match provided segments)
  - `start`: float (must be within segment bounds)
  - `end`: float (must be within segment bounds)
  - `reason`: string (optional, explanation for inclusion)
- **Style:** StyleConfig object
  - `pace`: "slow" | "normal" | "fast"
  - `captions`: boolean
  - `aspect_ratio`: "16:9" | "9:16" | "1:1"

### Prompt Engineering
- **Template:** Structured prompt that:
  1. Explains the edit task and constraints
  2. Shows the JSON schema format
  3. Lists retrieved segments with metadata
  4. Requests strict JSON output only (no prose)
- **Model:** Ollama (llama3 default, configurable)
- **Parameters:**
  - Temperature: 0.3 (deterministic)
  - Top-p: 0.9
  - Timeout: 60s per request

### Validation Engine
- **Constraints:**
  1. All clip_ids in timeline must exist in retrieved segments
  2. Timestamps must be within segment bounds (tolerance: ±0.1s)
  3. Timeline must not be empty
  4. Maximum 20 clips in plan (performance constraint)
- **Error handling:**
  - Invalid JSON → retry with schema reminder
  - Hallucination detected → use fallback plan
  - Timeout → return simple sequential plan of top segments

### CLI Commands (Phase 3)
- `python backend/main.py plan "prompt"` — generates edit plan from indexed segments
- Plan output saved to `data/edit_plan.json`

### Data Files
- `data/edit_plan.json` — generated plan ready for Phase 4 rendering

## Dependencies
- ollama (inference)
- pydantic (validation)
- json (parsing)

## Success Criteria
1. LLM generates valid JSON edit plans
2. Plans respect clip_id and timestamp constraints
3. Validation catches hallucinations and invalid timestamps
4. Fallback mechanism works when LLM fails
5. Plans are semantically meaningful given the user prompt
6. Timeout handling prevents hanging
7. Multiple plan generation attempts work reliably

## Notes
- Prompt engineering is critical for preventing hallucinations
- The template must be tested with multiple Ollama models
- Consider implementing a scoring mechanism to evaluate plan quality
- Cache prompts to avoid repeated LLM calls for similar queries
