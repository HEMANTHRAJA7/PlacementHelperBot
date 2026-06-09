---
phase: 1
slug: ingestion-security-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ^8.0.0 |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01-01 | 1 | SEC-02 | T-01-01 | Encrypts Google Refresh tokens in DB via AES-256 | unit | `pytest tests/test_auth.py::test_db_encryption` | ❌ W0 | ⬜ pending |
| 01-02-01 | 01-02 | 1 | INGST-01, SEC-01 | T-01-02 | Validates state parameter and OIDC JWT signatures on endpoints | unit | `pytest tests/test_auth.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 01-02 | 1 | SEC-01 | T-01-02 | Rejects webhooks with invalid or missing OIDC JWT signatures | security | `pytest tests/test_webhook.py::test_oidc_validation` | ❌ W0 | ⬜ pending |
| 01-03-01 | 01-03 | 2 | INGST-03, INGST-04 | — | Webhook receives Pub/Sub POST and enqueues to Celery | integration | `pytest tests/test_webhook.py::test_webhook_post` | ❌ W0 | ⬜ pending |
| 01-03-02 | 01-03 | 2 | INGST-05 | T-01-03 | Redis deduplication prevents duplicate event processing | integration | `pytest tests/test_webhook.py::test_idempotency` | ❌ W0 | ⬜ pending |
| 01-03-03 | 01-03 | 2 | INGST-06 | — | Tasks failing after 5 retries are routed to PostgreSQL DLQ | integration | `pytest tests/test_webhook.py::test_dlq_routing` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures for db session and Redis client mocks.
- [ ] `tests/test_auth.py` — unit and database encryption test stubs.
- [ ] `tests/test_webhook.py` — mock testing stubs for OIDC checking, Webhook ingestion, and Redis event deduplication.
- [ ] `pytest` install: `pip install pytest pytest-asyncio`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Google Console App Setup | INGST-01 | External GCP setup cannot be simulated locally. | Confirm GCP OAuth app credentials exist, redirect URI points to server `/api/v1/auth/callback`, and Test Users list includes email addresses. |
| GCP Pub/Sub Topic Publisher permissions | INGST-02 | GCP IAM permissions are cloud-based. | Send test publish message from GCP Console to verify Topic invokes the FastAPI webhook URL. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending YYYY-MM-DD
