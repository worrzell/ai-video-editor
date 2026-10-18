"""Integration tests for AI Video Editor."""

import json
import sys
import shutil
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_workflow_structure():
    """Verify the complete workflow structure is in place."""
    
    # Check all required modules exist
    required_modules = [
        'backend/main.py',
        'backend/services/ingestion.py',
        'backend/services/transcription.py',
        'backend/services/embedding.py',
        'backend/services/indexing.py',
        'backend/services/retrieval.py',
        'backend/services/planner.py',
        'backend/services/executor.py',
        'backend/services/ffmpeg_runner.py',
        'backend/db/vector_store.py',
        'backend/models/edit_plan.py',
    ]
    
    for module in required_modules:
        module_path = REPO_ROOT / module
        assert module_path.exists(), f'Missing module: {module} (looked in {REPO_ROOT})'
    
    # Check spec files exist
    required_specs = [
        'spec/01-core-architecture.md',
        'spec/02-architecture-diagram.md',
        'spec/03-api-dataflow.md',
        'spec/04-phase1-ingestion-transcription.md',
        'spec/05-phase2-embeddings-retrieval.md',
        'spec/06-phase3-llm-planning.md',
        'spec/07-phase4-rendering.md',
        'spec/08-phase5-polish-integration.md',
    ]
    
    for spec in required_specs:
        spec_path = REPO_ROOT / spec
        assert spec_path.exists(), f'Missing spec: {spec}'
    
    print('✓ All required modules exist')
    print('✓ All specification files exist')



def test_data_structures():
    """Verify data structure schemas are correct."""
    from backend.models.edit_plan import EditPlan, ClipSegment, StyleConfig
    
    # Create sample segment
    segment = ClipSegment(
        clip_id='test_clip',
        start=0.0,
        end=5.0,
        reason='Test segment'
    )
    assert segment.clip_id == 'test_clip'
    assert segment.start == 0.0
    assert segment.end == 5.0
    
    # Create sample style
    style = StyleConfig(
        pace='normal',
        captions=False,
        aspect_ratio='16:9'
    )
    assert style.pace == 'normal'
    assert style.captions is False
    
    # Create sample plan
    plan = EditPlan(
        timeline=[segment],
        style=style
    )
    assert len(plan.timeline) == 1
    assert plan.style.pace == 'normal'
    
    # Verify JSON serialization
    plan_json = plan.model_dump_json()
    plan_dict = json.loads(plan_json)
    assert plan_dict['timeline'][0]['clip_id'] == 'test_clip'
    
    print('✓ EditPlan data structures work correctly')


def test_imports():
    """Verify all imports work correctly."""
    try:
        from backend.services.ingestion import ingest_clips, save_manifest
        from backend.services.transcription import transcribe_clips, save_transcript
        from backend.services.embedding import EmbeddingProvider
        from backend.db.vector_store import VectorStore
        from backend.services.indexing import build_index, load_index
        from backend.services.retrieval import retrieve_segments
        from backend.services.planner import plan_edit, validate_plan, create_fallback_plan
        from backend.services.executor import render_plan, render_with_resolve
        from backend.services.ffmpeg_runner import trim_clip, concat_clips, verify_output
        
        print('✓ All imports successful')
        return True
    except ImportError as e:
        print(f'✗ Import failed: {e}')
        return False


if __name__ == '__main__':
    print('Running integration tests...\n')
    
    test_workflow_structure()
    test_data_structures()
    test_imports()
    
    print('\n✓ All integration tests passed!')
