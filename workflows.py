#!/usr/bin/env python3
"""
Quick start guide - common workflows for AI Video Editor.
Run this script to see recommendations based on what you want to do.
"""

workflows = {
    'create-highlight-reel': {
        'name': 'Create a Highlight Reel',
        'commands': [
            'python backend/main.py ingest ./data/clips/',
            'python backend/main.py process --whisper-model small',
            'python backend/main.py index',
            'python backend/main.py plan "create a fast-paced highlight reel with the best moments"',
            'python backend/main.py render',
        ],
        'time_estimate': '10-15 minutes',
        'requires': 'Ollama server running',
    },
    'search-specific-topic': {
        'name': 'Search for Specific Content',
        'commands': [
            'python backend/main.py ingest ./data/clips/',
            'python backend/main.py process --whisper-model tiny --language en',
            'python backend/main.py index',
            'python backend/main.py search "your search query" --top-k 10',
        ],
        'time_estimate': '5-10 minutes',
        'requires': None,
    },
    'fast-processing': {
        'name': 'Fast Processing (Quality vs Speed)',
        'commands': [
            'python backend/main.py ingest ./data/clips/',
            'python backend/main.py process --whisper-model tiny',  # 5 min for 5 clips
            'python backend/main.py index --embedding-model all-MiniLM-L6-v2',
            'python backend/main.py plan "your prompt"',
            'python backend/main.py render --output-path ./test_output.mp4',
        ],
        'time_estimate': '5-10 minutes',
        'requires': 'Ollama server running',
    },
    'high-quality': {
        'name': 'High Quality Output',
        'commands': [
            'python backend/main.py ingest ./data/clips/',
            'python backend/main.py process --whisper-model small',  # Better transcription
            'python backend/main.py index --embedding-model all-mpnet-base-v2',  # Better embeddings
            'python backend/main.py plan "your prompt"',
            'python backend/main.py render --output-path ./high_quality.mp4',
        ],
        'time_estimate': '30-45 minutes',
        'requires': 'Ollama server running',
    },
    'iterative-editing': {
        'name': 'Iterative Editing (Try Multiple Plans)',
        'commands': [
            'python backend/main.py ingest ./data/clips/',
            'python backend/main.py process --whisper-model small',
            'python backend/main.py index',
            '',
            '# Try different edits:',
            'python backend/main.py plan "fast action highlights"',
            'python backend/main.py render --output-path ./version1.mp4',
            '',
            'python backend/main.py plan "emotional moments and reactions"',
            'python backend/main.py render --output-path ./version2.mp4',
            '',
            'python backend/main.py plan "chronological with best moments"',
            'python backend/main.py render --output-path ./version3.mp4',
        ],
        'time_estimate': '20-30 minutes',
        'requires': 'Ollama server running',
    },
}

def show_workflow(key):
    """Display a specific workflow."""
    if key not in workflows:
        print(f'Unknown workflow: {key}')
        print(f'\nAvailable workflows: {", ".join(workflows.keys())}')
        return
    
    workflow = workflows[key]
    print(f'\n{"=" * 60}')
    print(f'WORKFLOW: {workflow["name"]}')
    print(f'{"=" * 60}')
    print(f'Time: {workflow["time_estimate"]}')
    if workflow['requires']:
        print(f'Requires: {workflow["requires"]}')
        print('\nTo start Ollama server:')
        print('  ollama serve')
    
    print(f'\nCommands:')
    print('-' * 60)
    for cmd in workflow['commands']:
        print(cmd)
    print('-' * 60)

def list_workflows():
    """List all available workflows."""
    print('\nAvailable Workflows:')
    print('=' * 60)
    for key, workflow in workflows.items():
        print(f'\n{key}:')
        print(f'  {workflow["name"]}')
        print(f'  Time: {workflow["time_estimate"]}')
        if workflow['requires']:
            print(f'  Requires: {workflow["requires"]}')

if __name__ == '__main__':
    import sys
    
    print('''
╔══════════════════════════════════════════════════════════════╗
║          AI VIDEO EDITOR - Quick Start Workflows             ║
╚══════════════════════════════════════════════════════════════╝
    ''')
    
    if len(sys.argv) > 1:
        show_workflow(sys.argv[1])
    else:
        list_workflows()
        print('\n\nUsage: python workflows.py <workflow-key>')
        print('Example: python workflows.py create-highlight-reel')
