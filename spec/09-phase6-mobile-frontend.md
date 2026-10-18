# Implementation Spec: Phase 6 — Mobile Frontend (Expo / React Native)

## Objective

Add a cross-platform mobile application (iOS + Android) using Expo (managed workflow) so users can upload video clips, generate AI edit plans, and download/share the rendered video — all from their phone.

The mobile app connects to the existing FastAPI backend over HTTP, authenticates via JWT Bearer token (stored securely on-device), and mirrors the web UI's three-step workflow through a four-tab bottom navigation bar.

---

## Scope

### New Top-Level Folder: `mobile/`

The entire mobile frontend lives in `mobile/` inside the monorepo. It is a standalone Expo project tracked as a Moon workspace project.

```
mobile/
├── App.tsx
├── app.json
├── babel.config.js
├── tsconfig.json
├── package.json
├── .env                       ← EXPO_PUBLIC_API_BASE_URL
├── .env.example
├── assets/
│   ├── icon.png
│   └── splash.png
└── src/
    ├── api/client.ts
    ├── store/authStore.ts
    ├── hooks/useStatus.ts
    ├── theme/colors.ts
    ├── screens/
    │   ├── UploadScreen.tsx
    │   ├── RenderScreen.tsx
    │   ├── LibraryScreen.tsx
    │   └── ProfileScreen.tsx
    └── components/
        ├── StatusBox.tsx
        └── PlanPreview.tsx
```

---

## Navigation Architecture

Bottom tab navigator (`@react-navigation/bottom-tabs`) with four tabs:

| Tab | Screen | Primary API Calls |
|---|---|---|
| 🎬 Upload | `UploadScreen` | `POST /api/upload` |
| ✨ Render | `RenderScreen` | `POST /api/render` |
| 📁 Library | `LibraryScreen` | `GET /api/status`, `GET /api/download/output` |
| 👤 Profile | `ProfileScreen` | `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/logout`, `GET /api/auth/me` |

Tab bar styling uses the dark-mode color tokens from `src/theme/colors.ts` to match the web UI aesthetic.

---

## Backend Change (Additive Only)

The `/api/auth/login` and `/api/auth/register` endpoints are modified to include `"token"` in the JSON response body alongside the existing HttpOnly cookie:

```python
json_resp = JSONResponse({
    "status": "success",
    "message": "...",
    "token": token,           # ← NEW: mobile clients read this
    "user": {...},
})
# HttpOnly cookie is still set — web UI unaffected
```

**Backward compatibility**: Web clients ignore `token` in the response body; mobile clients use it exclusively.

---

## Authentication Flow

```
Mobile App
  ↓ POST /api/auth/login { username, password }
Backend
  ↓ JSON { token, user, ... }  +  Set-Cookie: access_token (HttpOnly)
Mobile App
  ↓ SecureStore.setItemAsync('access_token', token)
  ↓ All subsequent requests: Authorization: Bearer <token>
```

Token is read from `expo-secure-store` on every API call via `src/api/client.ts`. On logout, `clearToken()` wipes it from the keychain.

---

## Screen Specifications

### UploadScreen

- **Purpose:** Pick video files from camera roll and upload them to the backend.
- **UI Elements:**
  - Header with clip count badge (from `useStatus`)
  - `[Choose Videos]` button → `ImagePicker.launchImageLibraryAsync({ mediaTypes: 'videos', allowsMultipleSelection: true })`
  - Upload progress indicator per file
  - Uploaded clip list (FlatList) showing filenames from `/api/status`
- **Auth Guard:** If not authenticated → show banner directing user to Profile tab.
- **API:** `POST /api/upload` as `multipart/form-data`

### RenderScreen

- **Purpose:** Enter a natural language prompt and trigger the Gemini render pipeline.
- **UI Elements:**
  - `TextInput` (multiline) for the edit prompt
  - `Switch` row for "Use DaVinci Resolve" (default: off)
  - `[Generate with Gemini & Render]` primary button
  - Loading spinner / activity indicator during render (30–120 s typical)
  - `StatusBox` showing render status message
  - `PlanPreview` collapsible section showing the returned edit plan JSON
- **On Success:** Navigate user to Library tab.
- **API:** `POST /api/render` with `application/x-www-form-urlencoded` body: `prompt=...&use_resolve=false`

### LibraryScreen

- **Purpose:** Browse uploaded clips and download/share the final rendered video.
- **UI Elements:**
  - Section A: "Uploaded Clips" FlatList (from `/api/status`)
  - Section B: "Final Output" card — shows `output_exists` status; `[Download & Share]` button enabled only when output ready
  - Pull-to-refresh (`RefreshControl`) triggers `useStatus.refresh()`
- **Download flow:**
  1. `FileSystem.downloadAsync(BASE_URL + '/api/download/output', cacheUri, { headers: { Authorization: 'Bearer ...' } })`
  2. `Sharing.shareAsync(localUri)`
- **API:** `GET /api/status`, `GET /api/download/output`

### ProfileScreen

- **Purpose:** Authentication (sign in / register / logout) and server info display.
- **Logged-out state:**
  - Username `TextInput`
  - Password `TextInput` (`secureTextEntry`)
  - Mode toggle: Sign In / Register
  - Error banner
- **Logged-in state:**
  - User badge (`👤 username`, role chip)
  - `[Log Out]` button → `POST /api/auth/logout` + `clearToken()`
- **Server Info section (read-only):**
  - API URL (`EXPO_PUBLIC_API_BASE_URL`)
  - Database type and model name from `/api/status`

---

## Shared Components

### `StatusBox`

Reusable info/status display card. Props: `message: string`, `variant: 'info' | 'error' | 'success'`. Styled with `Colors` tokens.

### `PlanPreview`

Collapsible section for displaying the JSON edit plan returned after a successful render. Uses `Animated` for expand/collapse. Renders a monospace `ScrollView` with the JSON string.

---

## State Management

### `authStore` (Zustand)

```typescript
interface AuthState {
  user: { id: string; username: string; role: string } | null;
  hydrated: boolean;
  login(user, token): Promise<void>;   // setToken + set user
  logout(): Promise<void>;             // clearToken + clear user
  setHydrated(v: boolean): void;
}
```

Hydration: On app startup (`App.tsx`), call `getToken()` + `GET /api/auth/me` to restore session before rendering.

### `useStatus` Hook

Polls `GET /api/status` every 5 seconds. Returns `{ data, error, refresh }`. Used by UploadScreen and LibraryScreen.

---

## Theme

All colors defined in `src/theme/colors.ts` match the web CSS custom properties exactly:

| Token | Value | Web CSS var |
|---|---|---|
| `bg` | `#070b15` | `--bg` |
| `surface` | `#0f172a` | `--surface` |
| `text` | `#e1e8ff` | `--text` |
| `muted` | `#94a3b8` | `--muted` |
| `primary` | `#38bdf8` | `--primary` |
| `danger` | `#f87171` | `--danger` |

---

## Permissions (app.json plugins)

```json
[
  ["expo-image-picker", { "photosPermission": "Allow AI Video Editor to access your videos." }],
  ["expo-media-library", { "photosPermission": "Allow AI Video Editor to save videos." }],
  "expo-secure-store"
]
```

---

## Environment Configuration

| Variable | Purpose | Default |
|---|---|---|
| `EXPO_PUBLIC_API_BASE_URL` | Backend server base URL | `http://localhost:8000` |

Set in `mobile/.env`. For physical device testing, use the machine's LAN IP (e.g. `http://192.168.1.42:8000`). For Android Emulator use `http://10.0.2.2:8000`.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `expo` | ~52.0.0 | Core SDK |
| `expo-image-picker` | ~15.0.0 | Camera roll video picker |
| `expo-file-system` | ~18.0.0 | Download final video |
| `expo-sharing` | ~12.0.0 | Share downloaded video |
| `expo-secure-store` | ~14.0.0 | JWT token keychain storage |
| `expo-media-library` | ~16.0.0 | Save permission |
| `expo-constants` | ~17.0.0 | Read env vars |
| `zustand` | ^5.0.0 | Auth state management |
| `react-native-paper` | ^5.12.0 | Material Design dark-theme components |
| `@react-navigation/native` | ^6.1.18 | Navigation core |
| `@react-navigation/bottom-tabs` | ^6.6.1 | Bottom tab navigator |
| `react-native-screens` | ~4.4.0 | Native screen optimization |
| `react-native-safe-area-context` | 4.12.0 | Safe area insets |

---

## Moon Integration

`mobile/moon.yml` defines tasks:

```yaml
language: javascript
type: application
tasks:
  install:   { command: npm install }
  start:     { command: npx expo start, local: true }
  android:   { command: npx expo start --android, local: true }
  ios:       { command: npx expo start --ios, local: true }
```

Root `moon.yml` adds `mobile: mobile` to `projects`.

---

## Success Criteria

1. `cd mobile && npm install && npx expo start` runs without errors
2. Expo Go app on device/simulator loads the 4-tab UI
3. Profile tab: sign in → user badge shown; logout → returns to sign-in form
4. Upload tab: pick video(s) → successful upload → clip appears in list
5. Render tab: enter prompt → render completes → plan JSON displayed
6. Library tab: Download button enabled after render → share sheet opens with video file
7. Session persists across app restarts (token in SecureStore)
8. Backend web UI at `http://localhost:8000` is unaffected (cookie auth still works)

---

## Notes

- This is Phase 6; Phases 1–5 cover the backend pipeline and web UI
- The mobile app is a thin client — all AI/processing happens on the backend
- Large video uploads over WiFi are acceptable for development; production deployment should consider chunked upload or pre-signed URLs
- No mobile-specific unit tests in this phase; manual verification via Expo Go is the primary validation method
