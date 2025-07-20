# 2. Logical Component Breakdown

## 2.1 Browser Extension Components

| Component                 | Tech                     | Description                                                                       | Key Interfaces                               |
| ------------------------- | ------------------------ | --------------------------------------------------------------------------------- | -------------------------------------------- |
| **Content‑Script Loader** | PyScript bootstrap       | Injects Pyodide, mounts Alpine app, listens to `submit`, `click` events           | `window.addEventListener('submit')` hooks    |
| **Prompt UI Module**      | Alpine.js + Tailwind     | Renders modal, handles Yes/No & Edit actions; measures render latency             | Emits `promptDecision` custom event          |
| **Adapter Registry**      | JSON file                | Maps site selectors (`textarea`, button) to handler strategies                    | Queried at startup; hot‑patch via URL config |
| **Extension Settings**    | Manifest v3 options page | Stores user prefs (toxicity threshold, locale, bypass toggle) in `chrome.storage` | Pub/Sub via `chrome.runtime.onMessage`       |
| **Telemetry Collector**   | Minimal JS               | Counts prompts shown/answered; saves to LocalStorage; optional Supabase push      | Debounced POST to `/metrics` edge function   |

## 2.2 Shared Core Library (`reflectpause_core`)

| Module                                                 | Responsibility                                                                      |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| **check(text****:str****) -> bool**                    | Returns `True` if text exceeds toxicity threshold or user has always‑prompt setting |
| **generate\_prompt(locale****:str****) -> PromptData** | Rotates CBT questions, returns localized prompt strings                             |
| **log\_decision(decision****:Enum****)**               | Writes anonymized entry (hash timestamp+decision) to local store interface          |
| **toxicity.engine**                                    | Strategy pattern: `ONNXEngine`, `PerspectiveAPIEngine`                              |

## 2.3 Discord Bot Components

| Component            | Tech                 | Description                                                        |
| -------------------- | -------------------- | ------------------------------------------------------------------ |
| **Gateway Listener** | discord.py           | Subscribes to `messageCreate`, `messageUpdate`                     |
| **Reflection Flow**  | discord.py FSM       | Deletes flagged message, sends DM prompt, waits for ✔️/✏️ reaction |
| **Storage Layer**    | SQLite via SQLModel  | Persists per‑user prompt counts, opt‑out status                    |
| **Admin Commands**   | discord.ext.commands | `!pause settings`, `!pause disable`, `/privacy delete`             |

## 2.4 Shared Assets & Tools

- **ONNX Models** – `detoxify_base_onnx.bin` (< 5 MB) loaded lazily into WebWorker & bot.
- **i18n JSON** – `en.json`, `vi.json` under `/locales`; contribution guide for PRs.
- **Playwright Smoke Tests** – Headless Chrome/Firefox scripts validating intercept on top 5 sites daily.
- **Dockerfile** – Multi‑stage build: Python slim → final Alpine with 20 MB image size.
- **Analytics Edge Function** – Supabase Function `/metrics` endpoint for opt‑in telemetry, aggregates anonymized prompt counts.

---
