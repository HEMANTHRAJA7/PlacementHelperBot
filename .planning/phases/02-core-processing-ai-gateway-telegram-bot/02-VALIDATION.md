---
phase: 2
slug: core-processing-ai-gateway-telegram-bot
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ^8.0.0 |
| **Config file** | pytest.ini |
| **Quick run command** | `python -m pytest tests/` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 02-01 | 1 | PROC-01, PROC-02 | — | N/A | integration | `python -m pytest tests/test_processing.py` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02-02 | 2 | PROC-03, PROC-04, PROC-05, PROC-06 | — | N/A | unit | `python -m pytest tests/test_gateway.py::test_ai_gateway_parsing` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02-02 | 2 | PROC-06 | — | N/A | unit | `python -m pytest tests/test_gateway.py::test_rate_limiting` | ❌ W0 | ⬜ pending |
| 02-03-01 | 02-03 | 3 | PROC-07, PROC-08 | — | Send Telegram notifications silently with HTML formatting | integration | `python -m pytest tests/test_bot.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_processing.py` — Stubs for Gmail retrieval and local pre-check matching.
- [ ] `tests/test_gateway.py` — Stubs for AI gateway parser, YAML prompt loader, token cost logger, and rate-limiting.
- [ ] `tests/test_bot.py` — Stubs for Telegram message HTML formatting and silent dispatcher.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Actual Telegram notification delivery | PROC-07 | Requires Telegram Bot Token connection to live chat. | Trigger a mock Celery task manually with a test user ID and verify a silent HTML message is received in the Telegram chat client. |
| Actual Gmail email downloading | PROC-01 | Requires active Google OAuth user access tokens. | Authenticate a test user and check that the Celery task downloads a real recent message successfully from Google APIs. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending YYYY-MM-DD
