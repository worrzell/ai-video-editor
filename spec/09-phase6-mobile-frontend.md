# Implementation Spec: Phase 6 — Mobile Frontend (Expo / React Native)

## Status: ✅ COMPLETE & VERIFIED

## Objective

Deliver a cross-platform mobile application (iOS + Android) using Expo (managed workflow) so creators can upload video clips, generate AI edit plans, monitor render progress, and download/share the rendered video — directly from their phone.

The mobile app connects to the FastAPI backend over HTTPS, authenticates via JWT Bearer token stored securely on-device (`expo-secure-store`), and provides a clean four-tab bottom navigation experience.

---

## Architecture & Technology Pinnings

- **Framework:** React Native `0.76.5` with Expo SDK `52` (managed workflow).
- **React Runtime:** `react@18.3.1` (ensures zero peer dependency conflicts with React Native core).
- **Navigation:** `@react-navigation/native` + `@react-navigation/bottom-tabs` (v7).
- **Secure Storage:** `expo-secure-store` for persistent JWT tokens.
- **Media Picking:** `expo-image-picker` with video selection and duration extraction.
- **Sharing & Downloads:** `expo-file-system` and `expo-sharing` for saving and sharing rendered videos.

---

## Directory Structure

```
mobile/
├── App.tsx                     # Main app root & bottom tab navigator
├── app.json                    # Expo project configuration
├── babel.config.js             # Babel compiler config
├── tsconfig.json               # TypeScript strict configuration
├── package.json                # Pinned dependencies
├── .env                        # Local environment (EXPO_PUBLIC_API_BASE_URL)
├── .env.example
├── assets/                     # App icon and splash screen
└── src/
    ├── api/client.ts           # Axios-like fetch wrapper with JWT Bearer injection
    ├── store/authStore.ts      # Zustand/hook-based reactive auth state
    ├── hooks/useStatus.ts      # SWR-style hook for polling server health
    ├── theme/colors.ts         # Dark-mode color palette matching Web UI
    ├── screens/
    │   ├── UploadScreen.tsx    # Camera roll picker & chunked file upload
    │   ├── RenderScreen.tsx    # Prompt input, DaVinci toggle, & 30s progress polling
    │   ├── LibraryScreen.tsx   # Video gallery, download, and native sharing
    │   └── ProfileScreen.tsx   # Sign in, registration, and server diagnostics
    └── components/
        ├── StatusBox.tsx       # Standardized alert/status card
        └── PlanPreview.tsx     # Formatted JSON edit plan timeline inspector
```

---

## Screen Specifications & Workflows

### 1. UploadScreen (`UploadScreen.tsx`)
- **Video Picker:** Launches native camera roll via `ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Videos })`.
- **Chunked Upload:** Uploads files in 20 MB slices using `FormData` to `/api/upload/chunk`, avoiding payload rejections on Cloud Run.
- **Visual Feedback:** Animated percentage progress bar indicating chunk number and transfer status.

### 2. RenderScreen (`RenderScreen.tsx`)
- **Prompt Form:** Multi-line text input for natural language editing instructions.
- **DaVinci Resolve Switch:** Toggle between standard FFmpeg rendering and DaVinci Resolve project generation.
- **30-Second Non-Overlapping Polling:**
  - Upon starting a render, begins querying `GET /api/render/progress`.
  - Next poll is scheduled 30 seconds after the previous request finishes via `setTimeout`, preventing request pileups and rate limits.
- **State Recovery on Screen Focus:** When navigating back to the Render screen, checks `/api/render/progress`; if a render is running, immediately displays the active step and resumes polling.
- **Plan Preview:** Displays timeline segments, cut timings, and pacing rules upon completion.

### 3. LibraryScreen (`LibraryScreen.tsx`)
- **Clip Gallery:** Lists all uploaded clips available on the server.
- **Download Final Video:** Downloads `final.mp4` via `FileSystem.downloadAsync` into the device's cache directory.
- **Native Share Sheet:** Triggers `Sharing.shareAsync` to export the edited video directly to Instagram, TikTok, YouTube Shorts, or Photos.

### 4. ProfileScreen (`ProfileScreen.tsx`)
- **Authentication:** Modal interface for Sign In and Account Registration.
- **Keychain Storage:** JWT Bearer tokens are persisted to `expo-secure-store` and cleared upon logout.
- **Diagnostics:** Displays connected server URL, database type (`sqlite`), and active LLM model (`gemini-3.8-flash`).

---

## Verification & Typecheck

The mobile frontend is continuously verified via the CI/CD pipeline:

```bash
# Typecheck
cd mobile
npx tsc --noEmit  # 0 errors
```
