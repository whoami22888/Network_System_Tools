# Network_System_Tools

# Network and System Tools

This project contains advanced network analysis and manipulation tools, as well as system manipulation and recovery tools.

Network System Tools is a mobile-first progressive web app (PWA), Android wrapper, and local AI bridge for authorized defensive security work. It can run in a browser, be installed to an Android home screen, be bundled into a WebView APK project, and connect to a free local Ollama model such as WhiteRabbitNeo.

## What this app provides

- **Android-accessible UI:** responsive layout, bottom navigation, safe-area spacing, and standalone display support.
- **Installable app shell:** web app manifest, home-screen icon, theme colors, and service worker caching.
- **Browser diagnostics:** safe connectivity and device-context checks that work within browser security limits.
- **Cloud/local endpoint setting:** a saved API base URL for future server-side diagnostic runners.
- **No paid tiers in this app:** local feature gates are intentionally configured as unlocked in `config/features.json`.
- **Android wrapper scaffold:** `android/` contains a WebView wrapper that bundles the PWA assets for APK builds.
- **Free local AI integration:** `backend/agent_server.py` bridges the UI to Ollama using the `whiterabbitneo` model by default.
- **Human consent controls:** terminal actions require an explicit consent checkbox and are shown on screen before execution.
- **Internet activity toggle:** network-capable terminal commands are blocked unless the user enables internet activity.
- **Findings logs and skill upload:** assistant actions can be logged locally, exported from the browser, and extended with uploaded JSON tool/skill definitions.
- **Restored built-in tool catalog:** `tools/builtin/` re-adds the project tool definitions for network analysis, system analysis, findings review, and recovery workflows.

> Browsers cannot perform raw ICMP ping, arbitrary port scans, packet capture, or privileged system recovery tasks directly. Those features should be implemented in an authenticated local/cloud agent or approved native wrapper and exposed through safe API routes. Only use this project on systems and networks where you have authorization.

## Run the browser app locally

```bash
python3 -m http.server 4173
```

Then open <http://localhost:4173>. On Android Chrome, use **Add to Home screen** or the in-app **Install app** prompt when available.

## Run the free Ollama / WhiteRabbitNeo bridge

Install and start Ollama, then pull or run a WhiteRabbitNeo-compatible model name available in your local Ollama installation:

```bash
ollama run whiterabbitneo
npm run agent
```

The bridge listens on <http://127.0.0.1:8787> by default. The PWA chat interface sends prompts to `/chat`, terminal requests to `/terminal`, settings to `/settings`, lists built-in/custom tools from `GET /tools`, and uploads JSON tools/skills to `POST /tools`.

## Android APK wrapper

The `android/` folder is a minimal native wrapper for using the bundled PWA like an Android app. `MainActivity` loads `file:///android_asset/www/index.html`, so the APK can open without requiring a hosted URL. Sync web changes into Android assets before building:

```bash
npm run sync:android
```

The Android Gradle configuration uses the direct `com.android.tools.build:gradle:8.5.2` classpath instead of the `com.android.application` plugin-marker module. This avoids the earlier `com.android.application:8.5.2` marker-resolution bottleneck. This repository does not include a Gradle wrapper binary; build with a local Android/Gradle installation or add a wrapper generated from a trusted Gradle install:

```bash
cd android
gradle assembleDebug
```

The produced debug APK is normally written under `android/app/build/outputs/apk/debug/`. Run `npm run check:android` first to verify the local Gradle configuration. If `assembleDebug` still fails, install/configure Android SDK and ensure the machine can reach Google's Maven repository for `com.android.tools.build:gradle:8.5.2`.

## Feature policy

`config/features.json` disables tiering for this app-owned interface and enables all current local app features, including AI chat, the visible action console, internet kill switch, findings logs, and tool upload/download. This should not be used to bypass payment, licensing, or access controls for third-party services; it only controls features implemented by this project.

## Restored built-in tools

The built-in tool catalog is stored as JSON under `tools/builtin/` so the original purpose of this repository remains visible and extendable:

- `connectivity_check` for authorized reachability diagnostics.
- `dns_lookup` for passive DNS review.
- `http_headers` for web service header hardening.
- `local_inventory` for local system context.
- `recovery_checklist` for guided recovery planning.
- `log_review` for local findings review.

The catalog is intentionally declarative: tools describe approved commands, consent requirements, internet-toggle requirements, and safety notes. Runtime execution still goes through the consent-gated bridge allowlist.

## Safety model

- The local bridge binds to `127.0.0.1` by default.
- Terminal execution is limited to a small command allowlist.
- Human consent is required for every terminal command.
- Internet-capable commands such as `curl`, `dig`, `nslookup`, and `traceroute` are blocked unless internet activity is enabled.
- Findings are written as JSON Lines under `logs/` when logging is enabled.
- Uploaded tools/skills are stored as JSON under `tools/` for review before use.

## Validate the static app

```bash
python3 -m json.tool manifest.webmanifest >/dev/null
python3 scripts/validate_static.py
```

Or run all checks through npm-compatible tooling:

```bash
npm run check
```

## Suggested cloud API shape

When the cloud backend is added, start with a minimal authenticated surface:

- `GET /health` — cloud agent status.
- `POST /diagnostics/connectivity` — server-side reachability checks for authorized targets.
- `POST /diagnostics/dns` — DNS lookup diagnostics.
- `GET /jobs/{id}` — async diagnostic job status and output.

Keep destructive, invasive, or privileged actions behind explicit authorization, audit logging, and rate limits.
