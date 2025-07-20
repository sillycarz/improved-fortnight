# 5. Technical Architecture Overview

## 5.1 High‑Level Stack

| Layer              | Technology                                                           | Purpose                                                           |
| ------------------ | -------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **UI / Client**    | **PyScript + Alpine.js** within WebExtension content‑script          | Render prompt modal, bind Yes/No actions, keep bundle lightweight |
| **Core Logic**     | **reflectpause\_core** (Python 3.12, type‑checked)                   | Prompt rotation, i18n, CBT logic, latency timer                   |
| **Toxicity Check** | **Detoxify‑Lite (onnx) in WebWorker** + optional **Perspective API** | On‑device fallback keeps cost \$0; API only for heavier analysis  |
| **Discord Bot**    | **discord.py 2.x** inside Docker alpine image                        | Intercept messages, send DM flow, re‑post on completion           |
| **Data Storage**   | LocalStorage (extension) / SQLite (bot)                              | Counts prompt events & engagement anonymized                      |
| **CI/CD**          | GitHub Actions → Playwright tests → web‑store upload via web-ext     | Ensures cross‑browser compatibility & auto‑deploy                 |

## 5.2 Component Relationships

```
[Browser DOM] ↔ [PyScript content‑script] ↔ [reflectpause_core] ↔ [Detoxify Lite]
                                             ↘ (optional) Perspective API ↙
[Discord Gateway] ↔ [discord.py bot] ↔ [reflectpause_core]
```

## 5.3 Extension Data Flow

1. User clicks **Post**.
2. Content‑script intercepts event; passes text to `reflectpause_core.check(text)`.
3. If `check` ⇒ **True** (needs reflection) → modal renders (Alpine.js + Tailwind CSS).
4. User answers; core logs decision to LocalStorage; DOM submission continues or cancelled.

## 5.4 Bot Data Flow

1. `messageCreate` event fires.
2. Bot calls `reflectpause_core.check(text)` (Detoxify / Perspective).
3. If flagged → delete message, DM prompt.
4. On ✔️, re‑post clean message; on ✏️, waits for edited text.

## 5.5 Deployment & Release Pipeline

- **Extension**: GitHub Action → Pyodide build → web‑ext lint → upload signed package to Chrome Store & AMO (unlisted beta).
- **Bot**: Docker build → GitHub Container Registry → Fly.io free tier deployment (stateless).
- **Versioning**: Semantic (MAJOR.MINOR.PATCH); automated changelog via conventional commits.

## 5.6 Security & Privacy

- No raw message text stored server‑side; hashed with SHA‑256 before analytics ping.
- CSP restricts extension to self; no eval.
- Permissions: `activeTab`, `storage`, specific site matches only.
- Discord bot complies with gateway intents; GDPR opt‑out command `/privacy delete`.

## 5.7 Technology Choices Rationale

- **PyScript** lets devs code prompt logic in Python while bundling to the browser via WebAssembly (pyodide); avoids split‑language cognitive load.
- **Alpine.js** for ultra‑light reactivity versus heavier React/Vue, preserving latency budget.
- **Detoxify‑Lite** ONNX model small (< 5 MB) enabling offline toxicity checks; Perspective API kept optional for richer analysis without cost explosion.
- **Docker/Fly.io** chosen for frictionless, cheap bot hosting and reproducible builds.

---
