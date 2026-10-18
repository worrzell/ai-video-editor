# AI Video Editor — Agents Reference

This document lists every AI agent available in this workspace, what they do, and when to use them. Agents are defined in `agents/` and are invocable via the `/` shortcut in the Copilot/Antigravity chat.

---

## Available Agents

| Agent | Invocation | Domain |
|---|---|---|
| [Video Editor](#-video-editor) | `/video-editor` | Color grading, effects, FFmpeg, DaVinci Resolve |
| [Video Analysis](#-video-analysis) | `/video-analysis` | Scene detection, metadata, quality assessment |
| [Audio Editor](#-audio-editor) | `/audio-editor` | Mixing, Foley, ADR, sound design |
| [Motion Graphics](#-motion-graphics) | `/motion-graphics` | Titles, overlays, kinetic typography |
| [Compression](#-compression) | `/compression` | Encoding, bitrate, delivery formats |
| [Mobile UI Developer](#-mobile-ui-developer) | `/mobile-ui` | Expo / React Native mobile frontend |

---

## 🎬 Video Editor

**File:** [`agents/video-editor.agent.md`](agents/video-editor.agent.md)

Handles all video post-production tasks: color grading, transitions, effects, and rendering pipelines via FFmpeg or DaVinci Resolve.

**Use when:** You need to trim clips, apply LUTs, add transitions, or configure rendering parameters.

---

## 🔍 Video Analysis

**File:** [`agents/video-analysis.agent.md`](agents/video-analysis.agent.md)

Analyzes video content: scene detection, metadata extraction, quality assessment, and automated feature extraction.

**Use when:** You need to understand what's in a video file, detect cuts, or extract technical metadata.

---

## 🎵 Audio Editor

**File:** [`agents/audio-editor.agent.md`](agents/audio-editor.agent.md)

Handles audio post-production: mixing, level balancing, Foley, ADR/dubbing, and music integration.

**Use when:** Audio tracks need editing, mixing, noise reduction, or synchronization with video.

---

## ✨ Motion Graphics

**File:** [`agents/motion-graphics.agent.md`](agents/motion-graphics.agent.md)

Creates motion graphics: title sequences, lower thirds, animated text overlays, and graphic elements.

**Use when:** You need visual overlays, captions, animated titles, or on-screen text effects.

---

## 📦 Compression

**File:** [`agents/compression.agent.md`](agents/compression.agent.md)

Optimizes video encoding: codec selection, bitrate tuning, delivery format preparation, and platform-specific settings (YouTube, Vimeo, social media).

**Use when:** The final video needs to be compressed, re-encoded, or prepared for a specific delivery platform.

---

## 📱 Mobile UI Developer

**File:** [`agents/mobile-ui.agent.md`](agents/mobile-ui.agent.md)

Develops and maintains the Expo / React Native mobile frontend (`mobile/`). Handles screens, navigation, API integration, state management, and mobile UX.

**Use when:** Any task involves the `mobile/` folder: adding screens, fixing navigation, updating the auth flow, or debugging Expo-specific issues.

---

## Workflow Delegation Guide

For complex projects, coordinate agents in this order:

```
1. Video Analysis → understand source content
2. Video Editor   → assemble & grade
3. Audio Editor   → mix & sweeten
4. Motion Graphics→ add titles & overlays
5. Compression    → prepare for delivery
6. Mobile UI      → update mobile app if needed
```

For the full delegation guide see: [`.github/instructions/video-production-workflow.instructions.md`](.github/instructions/video-production-workflow.instructions.md)

---

## Adding a New Agent

1. Create `agents/<name>.agent.md` with YAML frontmatter (`name`, `description`, `tools`, `model`, `user-invocable: true`)
2. Add an entry to this file
3. Add an entry to `.github/instructions/video-production-workflow.instructions.md`
4. Add the corresponding spec in `spec/` if the agent introduces a new subsystem
