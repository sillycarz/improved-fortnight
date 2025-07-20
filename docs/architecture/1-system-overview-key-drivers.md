# 1. System Overview & Key Drivers

## 1.1 Vision Recap

Deliver a **cross‑platform, Python‑centric** reflection tool that inserts a cognitive pause before harmful content is posted. MVP spans:

- **Browser Extension** (Chrome, Firefox, Edge) built with **PyScript/pyodide** content‑scripts.
- **Discord Bot** using **discord.py**.
- Shared **reflectpause\_core** Python library ensuring single‑source logic.

## 1.2 Architectural Goals

| Goal                        | Rationale                                                            |
| --------------------------- | -------------------------------------------------------------------- |
| **G1 Latency**              | Modal must render in ≤ 50 ms; bot DM round‑trip ≤ 250 ms.            |
| **G2 Cost‑Zero**            | Operate under \$10/month; on‑device inference default.               |
| **G3 Maintainability**      | Shared Python code; 80 % test coverage; CI gating.                   |
| **G4 Privacy & Compliance** | No PII storage; GDPR & CCPA respect; pass store reviews.             |
| **G5 Extensibility**        | Site adapters & locales via JSON registry; modular toxicity engines. |

## 1.3 Context Diagram (C4 Level 1)

```
+---------------------+        +-----------------------+
|      End User       |        |   Community Moderator |
|  Browser / Discord  |        |  Metrics Dashboard    |
+----------+----------+        +-----------+-----------+
           |                               |
           v                               ^
+----------+----------+        +-----------+-----------+
|  Browser Extension  |        |  Supabase (Opt‑in)    |
|  (PyScript)         |        |  Analytics Store      |
+----------+----------+        +-----------------------+
           |
           v
+----------+----------+
| reflectpause_core   |
+----------+----------+
           |
           v
+----------+----------+       +-----------------------+
| Detoxify Lite (onnx)|<----->|  Perspective API      |
+---------------------+       +-----------------------+
```

## 1.4 Key Trade‑Offs Considered

- **PyScript vs Pure JS**: Prioritized Python dev velocity over initial bundle size. Fallback JS modal specified if 50 ms budget breached.
- **On‑device vs Cloud NLP**: Default ONNX model keeps cost at zero; optional Perspective API provides richer accuracy at risk of quota fees.
- **LocalStorage vs Remote DB for metrics**: Chose LocalStorage + optional Supabase to respect privacy and budget.

---
