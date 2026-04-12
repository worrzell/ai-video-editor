# Copilot Instructions for AI Video Editor

## Purpose
Provide strict, repo-specific guardrails so the assistant stays focused on this app and does not divert into unrelated topics.

## Do this
- Work only within the `ai-video-editor` workspace and its files.
- Follow the project architecture and specs in the `spec/` folder.
- Ensure each new feature, file, or code area has a corresponding spec file in `spec/` before proceeding.
- For architecture-level details, create and maintain Mermaid diagrams in `spec/`.
- Prioritize implementing the app’s features over adding unrelated capabilities.
- Use concise, structured responses with headings, bullets, and short paragraphs.
- Prefer direct file edits and code changes over long explanations.
- Respect the user’s workflow and toolchain (Python, Typer, Poetry, Moon, FFmpeg, Ollama, Whisper, FAISS).
- Use `pyproject.toml` + Poetry as the canonical package management entrypoint for this repo.
- Use the root `moon.yml` workspace as the canonical task runner entrypoint for this repo.
- When asked to continue, continue from the current repo state and the most recent conversation context.
- Reference actual filenames and symbols in the workspace.

## Do not do this
- Do not propose unrelated tools, frameworks, or cloud services.
- Do not add features that are outside the current app scope unless the user explicitly asks.
- Do not overwrite code blindly without confirming existing file structure first.
- Do not give verbose or speculative answers; keep responses short and task-focused.
- Do not ignore the user’s preferred conventions about tool usage and code style.

## Behavior
- If a dependency or config is missing, state the issue and suggest the minimal fix.
- If a file does not exist, create it only when the user asks for a specific implementation.
- If the user asks why something was done, explain the exact reason and align with the repo’s current setup.
- Always check the current workspace before making assumptions.
