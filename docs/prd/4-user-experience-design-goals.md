# 4. User Experience & Design Goals

## 4.1 UX Principles

| Principle            | Description                                                     | Success Indicator              |
| -------------------- | --------------------------------------------------------------- | ------------------------------ |
| **Minimal Friction** | Prompt appears with ≤ 50 ms delay; does not disrupt typing flow | 95% prompts load within target |
| **Reflective Tone**  | Language encourages thoughtful response without shame           | ≥ 70% engagement rate          |
| **Visual Subtlety**  | Neutral colors, calm animation; avoids alert fatigue            | User survey ≥ 4/5 satisfaction |
| **Accessibility**    | WCAG 2.1 AA; keyboard navigation & screen reader labels         | A11y tests pass                |
| **Localization**     | Auto‑detect browser locale; easy community translation          | ≥ 2 languages supported        |

## 4.2 Extension UI Mock Elements

1. **Modal Overlay** – Semi‑transparent backdrop, centered card, three questions with radio buttons (Yes/No) and **Edit / Post Anyway** buttons.
2. **Settings Panel** – Accessible from toolbar icon: toggle toxicity gating, choose language, view privacy policy.
3. **Onboarding Tooltip** – 1‑time badge explaining the pause philosophy when extension installs.

## 4.3 Discord Bot Interaction Flow

```
User: <toxic message>
Bot (DM): Before we share that, a quick reflection:
1️⃣ Is it accurate & fair?
2️⃣ Could it harm someone?
3️⃣ Does it reflect who you want to be?
Reply with ✔️ to post or ✏️ to edit.
```

## 4.4 Design Constraints

- **Latency cap**: UI assets < 150 kB; animations CSS‑only (no heavy JS libs).
- **Branding**: Open‑source neutral palette (teal/grey); logo = hourglass inside speech bubble.
- **Mobile Friendly**: Extension modal responsive; Discord bot messages concise (< 240 chars).

---
