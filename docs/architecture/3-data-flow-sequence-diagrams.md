# 3. Data Flow & Sequence Diagrams

## 3.1 Extension Happy Path (Sequence)

```mermaid
sequenceDiagram
    participant User
    participant DOM as Browser DOM
    participant CS as Content‑Script
    participant Core as reflectpause_core
    participant UI as Prompt UI

    User->>DOM: Click "Post"
    DOM-->>CS: submit event
    CS->>Core: check(text)
    Core->>Core: Detoxify Lite inference
    Core-->>CS: NeedsPrompt = True/False
    alt NeedsPrompt == True
        CS->>UI: renderPrompt()
        UI-->>User: Modal with 3 questions
        User->>UI: Edit / Cancel / PostAnyway
        UI->>CS: promptDecision(decision)
        CS->>Core: log_decision(decision)
        alt decision == Edit/Cancel
            CS-->>DOM: Prevent default (no post)
        else decision == PostAnyway
            CS-->>DOM: continue submit
        end
    else NeedsPrompt == False
        CS-->>DOM: continue submit
    end
```

**Latency checkpoints**

1. `submit` → `check` round‑trip ≤ 25 ms.
2. Prompt modal render ≤ 25 ms.\
   Combined ≤ 50 ms target.

## 3.2 Discord Bot Happy Path (Sequence)

```mermaid
sequenceDiagram
    participant User
    participant DGW as Discord Gateway
    participant Bot
    participant Core as reflectpause_core

    User->>DGW: Sends message M
    DGW->>Bot: messageCreate(M)
    Bot->>Core: check(M.content)
    Core-->>Bot: NeedsPrompt = True/False
    alt NeedsPrompt == True
        Bot-->>DGW: delete M
        Bot->>User: DM with 3 questions
        User->>Bot: ✔️ or ✏️ + edited text
        alt ✔️ Post
            Bot-->>DGW: repost original M
        else ✏️
            Bot->>Core: check(edited)
            Core-->>Bot: decision
            Bot-->>DGW: repost edited text
        end
    else NeedsPrompt == False
        Bot-->>DGW: no action
    end
```

**Timing checkpoints**

- Gateway to DM prompt ≤ 150 ms.
- User response handling time excluded (user dependent).
- Repost round‑trip ≤ 100 ms.

## 3.3 Error & Edge‑Case Flows

| Scenario                     | Expected Behaviour                                                        |
| ---------------------------- | ------------------------------------------------------------------------- |
| **ONNX model fails to load** | Fallback to always‑prompt mode; telemetry flags `onnx_load_error`         |
| **Perspective API 429**      | Switch to ONNX engine until hourly cooldown expires                       |
| **User has JS disabled**     | Extension detects; degrades gracefully (no prompt) and warns in console   |
| **Discord DM disabled**      | Bot mentions user in channel with polite reminder and prompts public edit |

## 3.4 Data Privacy Flow

1. **Hashing** – `sha256(user_id + timestamp)` for log keys.
2. **Opt‑in analytics** – toggle in settings; default off.
3. **Deletion request** – `/privacy delete` wipes SQLite rows and disables future logging.

---
