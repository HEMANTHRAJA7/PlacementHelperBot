# Phase 1: Ingestion & Security Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 1-Ingestion & Security Foundation
**Areas discussed:** OAuth Onboarding, Encryption Key, Idempotency Caching, OAuth Callback UI

---

## OAuth Onboarding

| Option | Description | Selected |
|--------|-------------|----------|
| GCP Testing Mode | Keep app in testing, manually add friend emails to the GCP Test Users list, and bypass the Google warning screen | ✓ |
| Production Verification | Request Google verification to remove warning screens (requires privacy policy, domain registration, and Google review) | |

**User's choice:** GCP Testing Mode
**Notes:** Selected for simplicity and low overhead when serving a small cohort of 5-50 users.

---

## Encryption Key

| Option | Description | Selected |
|--------|-------------|----------|
| Environment Variable | Stored as a Railway env var; allows seamless 24/7 background worker operations without human intervention | ✓ |
| Passcode on Telegram | Derives the AES key from a passcode that the user sends to the Telegram bot upon bot startup | |

**User's choice:** Environment Variable
**Notes:** Storing the master key in the environment allows workers to autonomously decrypt tokens, enabling headless processing.

---

## Idempotency Caching

| Option | Description | Selected |
|--------|-------------|----------|
| 24-Hour Redis Cache | Cache historyIds/messageIds in Redis with a 24-hour TTL (sufficient to block Pub/Sub retry storms with minimal memory overhead) | ✓ |
| 7-Day Redis Cache | Cache events for 7 days to align with the watch subscription lifecycle | |
| Permanent DB Registry | Store a unique key for every processed message in a PostgreSQL table for lifetime duplicate avoidance | |

**User's choice:** 24-Hour Redis Cache
**Notes:** Optimal balance of memory protection and duplicate protection since Pub/Sub retries expire quickly.

---

## OAuth Callback UI

| Option | Description | Selected |
|--------|-------------|----------|
| Telegram Bot Link Initiation | User gets a personalized link from the Telegram bot (e.g. /login?tg_id=123) which initiates the OAuth flow and automatically links their Google credentials to their Telegram chat ID | ✓ |
| Standalone Web Page | Standard landing page with a login button; user manually enters their Telegram ID or username on the web form | |

**User's choice:** Telegram Bot Link Initiation
**Notes:** Ties the Telegram ID seamlessly and securely through the OAuth state parameter.

---

## the agent's Discretion

- Database schema details (indexes, types)
- Exact Celery DLQ name and queue parameter configuration
- Structure of the FastAPI redirect success page

## Deferred Ideas

- Standard web landing page logins without Telegram link triggers
- Cloud KMS integrations
