# 7. Open Issues & Appendices

## 7.1 Open Questions / Decisions Pending

| ID     | Question                                                                  | Owner             | Needed By | Notes                                                           |
| ------ | ------------------------------------------------------------------------- | ----------------- | --------- | --------------------------------------------------------------- |
| **Q1** | Will Chromium team approve PyScript‑heavy extension or require wasm flag? | Dev Lead          | Week 2    | Check with Chrome Web Store policies once prototype ready       |
| **Q2** | Final CBT prompt wording — plain vs slightly playful tone?                | UX Lead           | Week 4    | Run micro‑copy test on 50 users in Alpha                        |
| **Q3** | Ethics & Privacy review checklist – who signs off?                        | PM                | Week 7    | Engage volunteer privacy lawyer or use Mozilla community review |
| **Q4** | Perspective API quota estimate vs adoption target                         | Dev Lead          | Week 9    | Simulate 10 000 daily users and compute cost                    |
| **Q5** | Trademark clearance for hourglass‑speech‑bubble logo                      | Community Liaison | Week 10   | Ensure free use under permissive license                        |

## 7.2 Assumptions to Monitor

- PyScript + Pyodide will remain stable across Chrome/Firefox releases.
- Detoxify‑Lite ONNX model yields acceptable toxicity precision/recall for MVP.
- Moderator communities are willing to share incident statistics anonymously.

## 7.3 Glossary

- **CBT** — Cognitive Behavioral Therapy; psychological framework for reflection.
- **Prompt Engagement** — User selects *Edit* or answers questions before posting.
- **Detoxify‑Lite** — Small ONNX toxicity‑classification model used offline.
- **Perspective API** — Google‑hosted service scoring text toxicity 0–1.

## 7.4 Reference Links

1. GitHub repo draft → `github.com/reflectpause/bot`
2. CBT research meta‑analysis (2024) DOI: 10.1037/psyc.2023.0056
3. Detoxify model paper → arXiv: 2104.07412
4. Perspective API docs → developers.google.com/perspective

---
