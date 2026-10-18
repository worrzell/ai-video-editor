---
description: "Use when: video editing, post-production, color grading, audio mixing, motion graphics, compression, video analysis, content creation"
name: "Video Production Workflow"
applyTo: "**"
---
# Video Production Agent Delegation

This workspace uses specialized agents for different aspects of video production. Always delegate to the appropriate agent based on the task:

## Agent Selection Guide

### 🎬 **Video Editor Agent** (`/video-editor`)
**Use for:**
- Color grading and color correction
- Video transitions and effects
- Rendering with FFmpeg or DaVinci Resolve
- Video editing workflows and pipelines
- Professional post-production tasks

**Examples:**
- "Apply a cinematic color grade to this footage"
- "Add smooth transitions between clips"
- "Render video with professional quality settings"

### 🔍 **Video Analysis Agent** (`/video-analysis`)
**Use for:**
- Scene detection and content analysis
- Metadata extraction from video files
- Quality assessment and technical analysis
- Automated video processing and feature extraction

**Examples:**
- "Detect scene changes in this video"
- "Extract metadata from video files"
- "Analyze video quality and compression artifacts"

### 🎵 **Audio Editor Agent** (`/audio-editor`)
**Use for:**
- Audio mixing and level balancing
- Foley effects and sound design
- ADR/dubbing and voice replacement
- Music integration and scoring

**Examples:**
- "Mix dialogue and background audio"
- "Create sound effects for this scene"
- "Balance audio levels for broadcast"

### ✨ **Motion Graphics Agent** (`/motion-graphics`)
**Use for:**
- Title sequences and credits
- Lower thirds and text overlays
- Animated typography and text effects
- Graphic elements and visual design

**Examples:**
- "Create animated opening titles"
- "Design lower thirds for interviews"
- "Add kinetic typography effects"

### 📦 **Compression Agent** (`/compression`)
**Use for:**
- Video encoding optimization
- Bitrate and quality balancing
- Delivery format preparation
- Platform-specific compression settings

**Examples:**
- "Optimize video for web delivery"
- "Compress for YouTube upload"
- "Create streaming-ready formats"

### 📱 **Mobile UI Developer Agent** (`/mobile-ui`)
**Use for:**
- Any work inside the `mobile/` folder (Expo / React Native)
- Adding or modifying screens (Upload, Render, Library, Profile tabs)
- Mobile navigation changes (bottom tab bar, stack screens)
- Mobile auth flow (SecureStore, Zustand authStore, JWT Bearer token)
- Camera roll video picker integration
- Download and share of final video on device
- Theme / styling updates to the mobile app

**Examples:**
- "Add a settings screen to the mobile app"
- "Fix the auth token not persisting after app restart"
- "Add upload progress bar to the Upload tab"
- "Update the Library tab to show render job history"

## Workflow Integration

For complex video projects, coordinate between agents:
1. **Analysis** → Understand content and requirements
2. **Editing** → Core video assembly and effects
3. **Audio** → Sound design and mixing
4. **Graphics** → Titles and visual elements
5. **Compression** → Final delivery optimization
6. **Mobile UI** → Update mobile app if needed

## Project Standards

- Use FFmpeg for automated processing and basic editing
- Use DaVinci Resolve for professional color grading and advanced effects
- Maintain high-quality outputs with appropriate compression
- Follow broadcast standards for audio levels and video formats