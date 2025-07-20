# Product Requirements Document — Reflective Pause Bot

## 1. Purpose & Problem Statement

Social platforms amplify impulsive reactions, fueling toxicity that damages community well‑being. The Reflective Pause Bot introduces a brief, psychology‑based pause—three CBT‑inspired questions—before a message is posted. This nudge helps users self‑regulate, aiming to reduce toxic incidents by at least **40 %** in pilot communities while keeping infrastructure costs near zero.

## 2. Objectives & Success Criteria

| #      | Objective                                | Metric | Target                            | Timeline    |
| ------ | ---------------------------------------- | ------ | --------------------------------- | ----------- |
| **O1** | Cut toxic incidents in pilot communities | M1     | ≥ 40% reduction                   | 3 months    |
| **O2** | Maintain low infrastructure cost         | M2     | ≤ \$100 total                     | MVP release |
| **O3** | Achieve meaningful adoption              | M3     | ≥ 500 installs + 3 Discord pilots | 3 months    |
| **O4** | Prove user engagement                    | M4     | ≥ 70% prompts answered            | MVP review  |
| **O5** | Seed OSS community                       | M5     | ≥ 5 contributors, 100 stars       | 2 months    |

## 3. Core Features & Requirements

| ID     | Requirement                              | Priority |
| ------ | ---------------------------------------- | -------- |
| **R1** | Browser extension with 3-question prompt | P1       |
| **R2** | Python Discord bot with DM prompt        | P1       |
| **R3** | Shared Python core library               | P1       |
| **R4** | Perspective API integration              | P2       |
| **R5** | Localization support                     | P2       |
| **R6** | Opt-in analytics                         | P3       |

## 4. User Experience & Design Goals

### 4.1 UX Principles

| Principle            | Description                                                     | Success Indicator              |
| -------------------- | --------------------------------------------------------------- | ------------------------------ |
| **Minimal Friction** | Prompt appears with ≤ 50 ms delay; does not disrupt typing flow | 95% prompts load within target |
| **Reflective Tone**  | Language encourages thoughtful response without shame           | ≥ 70% engagement rate          |
| **Visual Subtlety**  | Neutral colors, calm animation; avoids alert fatigue            | User survey ≥ 4/5 satisfaction |
| **Accessibility**    | WCAG 2.1 AA; keyboard navigation & screen reader labels         | A11y tests pass                |
| **Localization**     | Auto‑detect browser locale; easy community translation          | ≥ 2 languages supported        |

### 4.2 Extension UI Mock Elements

1. **Modal Overlay** – Semi‑transparent backdrop, centered card, three questions with radio buttons (Yes/No) and **Edit / Post Anyway** buttons.
2. **Settings Panel** – Accessible from toolbar icon: toggle toxicity gating, choose language, view privacy policy.
3. **Onboarding Tooltip** – 1‑time badge explaining the pause philosophy when extension installs.

### 4.3 Discord Bot Interaction Flow

```
User: <toxic message>
Bot (DM): Before we share that, a quick reflection:
1️⃣ Is it accurate & fair?
2️⃣ Could it harm someone?
3️⃣ Does it reflect who you want to be?
Reply with ✔️ to post or ✏️ to edit.
```

### 4.4 Design Constraints

- **Latency cap**: UI assets < 150 kB; animations CSS‑only (no heavy JS libs).
- **Branding**: Open‑source neutral palette (teal/grey); logo = hourglass inside speech bubble.
- **Mobile Friendly**: Extension modal responsive; Discord bot messages concise (< 240 chars).

---

## 5. Technical Architecture Overview

### 5.1 High‑Level Stack

| Layer              | Technology                                                           | Purpose                                                           |
| ------------------ | -------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **UI / Client**    | **PyScript + Alpine.js** within WebExtension content‑script          | Render prompt modal, bind Yes/No actions, keep bundle lightweight |
| **Core Logic**     | **reflectpause\_core** (Python 3.12, type‑checked)                   | Prompt rotation, i18n, CBT logic, latency timer                   |
| **Toxicity Check** | **Detoxify‑Lite (onnx) in WebWorker** + optional **Perspective API** | On‑device fallback keeps cost \$0; API only for heavier analysis  |
| **Discord Bot**    | **discord.py 2.x** inside Docker alpine image                        | Intercept messages, send DM flow, re‑post on completion           |
| **Data Storage**   | LocalStorage (extension) / SQLite (bot)                              | Counts prompt events & engagement anonymized                      |
| **CI/CD**          | GitHub Actions → Playwright tests → web‑store upload via web-ext     | Ensures cross‑browser compatibility & auto‑deploy                 |

### 5.2 Component Relationships

```
[Browser DOM] ↔ [PyScript content‑script] ↔ [reflectpause_core] ↔ [Detoxify Lite]
                                             ↘ (optional) Perspective API ↙
[Discord Gateway] ↔ [discord.py bot] ↔ [reflectpause_core]
```

### 5.3 Extension Data Flow

1. User clicks **Post**.
2. Content‑script intercepts event; passes text to `reflectpause_core.check(text)`.
3. If `check` ⇒ **True** (needs reflection) → modal renders (Alpine.js + Tailwind CSS).
4. User answers; core logs decision to LocalStorage; DOM submission continues or cancelled.

### 5.4 Bot Data Flow

1. `messageCreate` event fires.
2. Bot calls `reflectpause_core.check(text)` (Detoxify / Perspective).
3. If flagged → delete message, DM prompt.
4. On ✔️, re‑post clean message; on ✏️, waits for edited text.

### 5.5 Deployment & Release Pipeline

- **Extension**: GitHub Action → Pyodide build → web‑ext lint → upload signed package to Chrome Store & AMO (unlisted beta).
- **Bot**: Docker build → GitHub Container Registry → Fly.io free tier deployment (stateless).
- **Versioning**: Semantic (MAJOR.MINOR.PATCH); automated changelog via conventional commits.

### 5.6 Security & Privacy

- No raw message text stored server‑side; hashed with SHA‑256 before analytics ping.
- CSP restricts extension to self; no eval.
- Permissions: `activeTab`, `storage`, specific site matches only.
- Discord bot complies with gateway intents; GDPR opt‑out command `/privacy delete`.

### 5.7 Technology Choices Rationale

- **PyScript** lets devs code prompt logic in Python while bundling to the browser via WebAssembly (pyodide); avoids split‑language cognitive load.
- **Alpine.js** for ultra‑light reactivity versus heavier React/Vue, preserving latency budget.
- **Detoxify‑Lite** ONNX model small (< 5 MB) enabling offline toxicity checks; Perspective API kept optional for richer analysis without cost explosion.
- **Docker/Fly.io** chosen for frictionless, cheap bot hosting and reproducible builds.

---

## 6. Release Plan & Timeline

### 6.1 Phased Roll‑Out Strategy

| Phase               | Weeks | Audience                                             | Key Goals                                              | Exit Criteria                                           |
| ------------------- | ----- | ---------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------- |
| **Tech Spike**      | 1‑2   | Internal devs                                        | Benchmark PyScript latency, verify Detoxify model size | Core lib prototype passes latency < 50 ms               |
| **Alpha (Private)** | 3‑6   | Core team + 2 trusted Discord servers                | Implement F1‑F3; gather functional feedback            | Prompt works on Reddit/Twitter + Discord DM flow stable |
| **Closed Pilot**    | 7‑8   | 2‑3 additional mod‑led communities                   | Validate engagement & toxicity reduction on real users | ≥ 30 % incident drop, 70 % prompt engagement            |
| **Public Beta**     | 9‑11  | Chrome/Firefox unlisted store; GitHub public release | Broader bug discovery, crowd‑source translations       | < 5% crash reports, ≥ 2 extra locales added             |
| **v1.0 GA**         | 12    | General public listing                               | Meet adoption & cost KPIs; security review complete    | O1‑O5 metrics on track, store approvals granted         |

### 6.2 Detailed 12‑Week Timeline

| Week | Milestone                    | Owner            | Notes                                             |
| ---- | ---------------------------- | ---------------- | ------------------------------------------------- |
| 1‑2  | Tech Spike & Benchmarks      | Dev Lead         | PyScript vs JS fallback decision by Week 2        |
| 3‑4  | Core Library v0.1            | Python Dev       | 80 % unit‑test coverage target                    |
| 5‑6  | Browser Extension Alpha      | Extension Squad  | Reddit & Twitter adapters; local Detoxify only    |
| 7    | Discord Bot Alpha            | Bot Maintainer   | Hosted on Fly.io free tier                        |
| 8    | Closed Pilot Launch          | PM + Moderators  | Data collection plan approved by Ethics checklist |
| 9‑10 | Feedback Iteration           | Cross‑functional | Address latency bugs, add bypass setting          |
| 11   | Public Beta Release          | PM               | Unlisted store submissions, GitHub issues triage  |
| 12   | v1.0 Launch & Metrics Review | Stakeholders     | Go/No‑Go on marketing push                        |

### 6.3 Dependency & Risk Gates

- **Latency Gate**: PyScript init < 50 ms (95th percentile) or fallback to JS modal before Beta.
- **Privacy Gate**: No PII logged; external audit before Public Beta.
- **Budget Gate**: Perspective API cost < \$10/month at Public Beta scale; else switch to offline‑only mode.
- **Security Gate**: Extension passes Mozilla automated scanner and manual AMO review.

### 6.4 Communications Plan

- **Changelog** updated via conventional commits → auto‑generated Markdown on GitHub.
- **Beta Announce**: r/InternetIsBeautiful, Product Hunt upcoming page.
- **v1.0 Launch**: Blog post + Twitter thread; cross‑post to Dev.to and HN.

---

## 7. Open Issues & Appendices

### 7.1 Open Questions / Decisions Pending

| ID     | Question                                                                  | Owner             | Needed By | Notes                                                           |
| ------ | ------------------------------------------------------------------------- | ----------------- | --------- | --------------------------------------------------------------- |
| **Q1** | Will Chromium team approve PyScript‑heavy extension or require wasm flag? | Dev Lead          | Week 2    | Check with Chrome Web Store policies once prototype ready       |
| **Q2** | Final CBT prompt wording — plain vs slightly playful tone?                | UX Lead           | Week 4    | Run micro‑copy test on 50 users in Alpha                        |
| **Q3** | Ethics & Privacy review checklist – who signs off?                        | PM                | Week 7    | Engage volunteer privacy lawyer or use Mozilla community review |
| **Q4** | Perspective API quota estimate vs adoption target                         | Dev Lead          | Week 9    | Simulate 10 000 daily users and compute cost                    |
| **Q5** | Trademark clearance for hourglass‑speech‑bubble logo                      | Community Liaison | Week 10   | Ensure free use under permissive license                        |

### 7.2 Assumptions to Monitor

- PyScript + Pyodide will remain stable across Chrome/Firefox releases.
- Detoxify‑Lite ONNX model yields acceptable toxicity precision/recall for MVP.
- Moderator communities are willing to share incident statistics anonymously.

### 7.3 Glossary

- **CBT** — Cognitive Behavioral Therapy; psychological framework for reflection.
- **Prompt Engagement** — User selects *Edit* or answers questions before posting.
- **Detoxify‑Lite** — Small ONNX toxicity‑classification model used offline.
- **Perspective API** — Google‑hosted service scoring text toxicity 0–1.

### 7.4 Reference Links

1. GitHub repo draft → `github.com/reflectpause/bot`
2. CBT research meta‑analysis (2024) DOI: 10.1037/psyc.2023.0056
3. Detoxify model paper → arXiv: 2104.07412
4. Perspective API docs → developers.google.com/perspective

---

## 2. Logical Component Breakdown

### 2.1 Browser Extension Components

| Component                 | Tech                     | Description                                                                       | Key Interfaces                               |
| ------------------------- | ------------------------ | --------------------------------------------------------------------------------- | -------------------------------------------- |
| **Content‑Script Loader** | PyScript bootstrap       | Injects Pyodide, mounts Alpine app, listens to `submit`, `click` events           | `window.addEventListener('submit')` hooks    |
| **Prompt UI Module**      | Alpine.js + Tailwind     | Renders modal, handles Yes/No & Edit actions; measures render latency             | Emits `promptDecision` custom event          |
| **Adapter Registry**      | JSON file                | Maps site selectors (`textarea`, button) to handler strategies                    | Queried at startup; hot‑patch via URL config |
| **Extension Settings**    | Manifest v3 options page | Stores user prefs (toxicity threshold, locale, bypass toggle) in `chrome.storage` | Pub/Sub via `chrome.runtime.onMessage`       |
| **Telemetry Collector**   | Minimal JS               | Counts prompts shown/answered; saves to LocalStorage; optional Supabase push      | Debounced POST to `/metrics` edge function   |

### 2.2 Shared Core Library (`reflectpause_core`)

| Module                                                 | Responsibility                                                                      |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| **check(text****:str****) -> bool**                    | Returns `True` if text exceeds toxicity threshold or user has always‑prompt setting |
| **generate\_prompt(locale****:str****) -> PromptData** | Rotates CBT questions, returns localized prompt strings                             |
| **log\_decision(decision****:Enum****)**               | Writes anonymized entry (hash timestamp+decision) to local store interface          |
| **toxicity.engine**                                    | Strategy pattern: `ONNXEngine`, `PerspectiveAPIEngine`                              |

### 2.3 Discord Bot Components

| Component            | Tech                 | Description                                                        |
| -------------------- | -------------------- | ------------------------------------------------------------------ |
| **Gateway Listener** | discord.py           | Subscribes to `messageCreate`, `messageUpdate`                     |
| **Reflection Flow**  | discord.py FSM       | Deletes flagged message, sends DM prompt, waits for ✔️/✏️ reaction |
| **Storage Layer**    | SQLite via SQLModel  | Persists per‑user prompt counts, opt‑out status                    |
| **Admin Commands**   | discord.ext.commands | `!pause settings`, `!pause disable`, `/privacy delete`             |

### 2.4 Shared Assets & Tools

- **ONNX Models** – `detoxify_base_onnx.bin` (< 5 MB) loaded lazily into WebWorker & bot.
- **i18n JSON** – `en.json`, `vi.json` under `/locales`; contribution guide for PRs.
- **Playwright Smoke Tests** – Headless Chrome/Firefox scripts validating intercept on top 5 sites daily.
- **Dockerfile** – Multi‑stage build: Python slim → final Alpine with 20 MB image size.

---
