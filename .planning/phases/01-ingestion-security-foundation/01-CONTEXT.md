# Phase 1: Ingestion & Security Foundation - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up linked Gmail OAuth accounts, Google Cloud Pub/Sub push webhooks, AES-256 database credential encryption, Redis idempotency keys, and Celery background queue processing with Dead-Letter Queue (DLQ) retry handlers.

</domain>

<decisions>
## Implementation Decisions

### OAuth Onboarding
- **D-01:** Google Cloud Platform (GCP) OAuth App status will be kept in "Testing" mode. No production Google verification review is required.
- **D-02:** User email addresses (5-50 users) will be manually added to the "Test Users" list inside Google Cloud Console.
- **D-03:** Users will bypass Google's "Unverified App / Dangerous" warning screen manually during onboarding.

### Encryption Key Management
- **D-04:** The AES-256 master key for decrypting OAuth refresh tokens and student IDs will be loaded from a Railway environment variable (`AES_SECRET_KEY`).
- **D-05:** Background Celery workers will decrypt credentials out-of-band to query the Gmail API without human/bot prompt interaction.

### Idempotency Caching
- **D-06:** Gmail `historyId` and Pub/Sub `message_id` values will be cached in Redis with a 24-hour Time-To-Live (TTL) to block duplicate events and retry storms.

### OAuth Callback UI & Telegram Linking
- **D-07:** The OAuth flow begins by sending a command to the Telegram Bot, which returns a parameterized OAuth URL containing the user's Telegram ID as the state (e.g. `/login?tg_id=123`).
- **D-08:** The FastAPI `/callback` redirect URL processes the authorization code, exchanges it for a refresh token, encrypts the credentials, maps them to the Telegram chat ID in PostgreSQL, and alerts the user on Telegram that onboarding is complete.

### the agent's Discretion
- Database schema details (indexes, types)
- Exact Celery DLQ name and queue parameter configuration
- Structure of the FastAPI redirect success page

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- [PROJECT.md](file:///.planning/PROJECT.md) — Core value, constraints, and architecture diagram
- [REQUIREMENTS.md](file:///.planning/REQUIREMENTS.md) — Traceability mapping and v1 requirements (`INGST-01` to `INGST-06`, `SEC-01`, `SEC-02`)
- [ROADMAP.md](file:///.planning/ROADMAP.md) — Phase 1 scope boundaries and success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None (greenfield project initialization)

### Established Patterns
- None (first development phase)

### Integration Points
- FastAPI endpoint will receive Google Pub/Sub push messages and link to Redis cache and Celery broker.
- Database tables (PostgreSQL) will save encrypted OAuth credentials mapped to Telegram chat IDs.

</code_context>

<deferred>
## Deferred Ideas

- Standard web landing page logins without Telegram link triggers — out of scope.
- Cloud KMS integrations — deferred in favor of environment variables.

</deferred>

---

*Phase: 01-ingestion-security-foundation*
*Context gathered: 2026-06-09*
