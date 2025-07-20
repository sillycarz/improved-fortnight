# 5. Non‑Functional Requirements Validation & Appendices

## 5.1 NFR Traceability Matrix

| NFR                                    | Source (PRD) | Validation Method                                      | Tool / Metric              | Pass Threshold |
| -------------------------------------- | ------------ | ------------------------------------------------------ | -------------------------- | -------------- |
| **Latency** ≤ 50 ms modal (< 95th pct) | PRD NX1      | Automated Playwright trace                             | 95 % of 10 000 samples     | ✅ ≤ 50 ms      |
| **Bot DM Round‑Trip** ≤ 250 ms         | PRD NX1      | Locust load test (100 VUs)                             | Avg ≤ 180 ms; p95 ≤ 250 ms | ✅ both         |
| **Privacy (No PII stored)**            | PRD NX2      | Manual code audit + GDPR checklist                     | Zero PII findings          | ✅              |
| **Maintainability 80 % coverage**      | PRD NX3      | `pytest --cov` CI gate                                 | `coverage >= 80`           | ✅              |
| **Cross‑Browser Compatibility**        | PRD NX4      | Playwright matrix (Chrome v115, Firefox ESR, Edge 125) | All smoke tests green      | ✅              |

## 5.2 Performance Test Plan

1. **Extension Latency Bench** – Playwright script posts 1 000 randomized comments on Reddit & Twitter; captures `PerformanceObserver` marks.
2. **ONNX Model Load** – Browser dev‑tools performance profile; target < 15 ms compile.
3. **Bot Load** – Locust spawns 100 virtual users sending 10 msgs/sec for 5 min on Fly staging.

## 5.3 Security Checklist Summary

-

## 5.4 Open Technical Debt Items

| ID      | Debt                        | Impact                          | Plan                                  |
| ------- | --------------------------- | ------------------------------- | ------------------------------------- |
| **TD1** | PyScript bundle size 600 kB | Increases cold‑start on slow 3G | Explore PyScript split‑loader post‑GA |
| **TD2** | No mobile keyboard support  | Loss of mobile coverage         | Prototype Gboard plug‑in in Q2 2026   |

## 5.5 Glossary Additions

- **p95 latency** – 95th percentile response time.
- **OIDC** – OpenID Connect; GitHub Actions auth method.
- **Playwright** – Headless browser automation used for E2E tests.

---

**Architecture Document Complete** – all sections drafted.

