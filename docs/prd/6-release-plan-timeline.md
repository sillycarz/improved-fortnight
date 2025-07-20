# 6. Release Plan & Timeline

## 6.1 Phased Roll‑Out Strategy

| Phase               | Weeks | Audience                                             | Key Goals                                              | Exit Criteria                                           |
| ------------------- | ----- | ---------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------- |
| **Tech Spike**      | 1‑2   | Internal devs                                        | Benchmark PyScript latency, verify Detoxify model size | Core lib prototype passes latency < 50 ms               |
| **Alpha (Private)** | 3‑6   | Core team + 2 trusted Discord servers                | Implement F1‑F3; gather functional feedback            | Prompt works on Reddit/Twitter + Discord DM flow stable |
| **Closed Pilot**    | 7‑8   | 2‑3 additional mod‑led communities                   | Validate engagement & toxicity reduction on real users | ≥ 30 % incident drop, 70 % prompt engagement            |
| **Public Beta**     | 9‑11  | Chrome/Firefox unlisted store; GitHub public release | Broader bug discovery, crowd‑source translations       | < 5% crash reports, ≥ 2 extra locales added             |
| **v1.0 GA**         | 12    | General public listing                               | Meet adoption & cost KPIs; security review complete    | O1‑O5 metrics on track, store approvals granted         |

## 6.2 Detailed 12‑Week Timeline

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

## 6.3 Dependency & Risk Gates

- **Latency Gate**: PyScript init < 50 ms (95th percentile) or fallback to JS modal before Beta.
- **Privacy Gate**: No PII logged; external audit before Public Beta.
- **Budget Gate**: Perspective API cost < \$10/month at Public Beta scale; else switch to offline‑only mode.
- **Security Gate**: Extension passes Mozilla automated scanner and manual AMO review.

## 6.4 Communications Plan

- **Changelog** updated via conventional commits → auto‑generated Markdown on GitHub.
- **Beta Announce**: r/InternetIsBeautiful, Product Hunt upcoming page.
- **v1.0 Launch**: Blog post + Twitter thread; cross‑post to Dev.to and HN.

---
