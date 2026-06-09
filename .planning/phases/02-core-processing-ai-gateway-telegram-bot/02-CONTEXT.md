# Phase 2: Core Processing, AI Gateway, & Telegram Bot - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch email body and metadata via Gmail API in Celery tasks using encrypted refresh tokens, perform local deterministic pre-check matching, run centralized Gemini Flash AI classification and JSON metadata extraction, and dispatch silent HTML priority alerts (Offer > Shortlist > Interview > Assessment > Opportunity) to students on Telegram.

</domain>

<decisions>
## Implementation Decisions

### AI Gateway Model & Cost Tracking
- **D-09:** Use `gemini-2.0-flash` as the primary engine for email classification and metadata extraction.
- **D-10:** Persist token usage (input/output tokens) and computed USD costs in a dedicated PostgreSQL database table (`ai_usage_logs`).
- **D-11:** If the primary Gemini model fails, retry up to 3 times with exponential backoff (5s, 30s, 120s). If it remains unavailable, fall back to local deterministic rule-based parsing. If classification confidence is insufficient, send a generic placement alert: *"Placement-related email detected. Please check your VIT mail."* Log the details to audit logs, and only route the task to the Celery DLQ if both the AI and deterministic processing fail.

### Telegram Notification Styling & Priority
- **D-12:** Telegram notifications must be formatted in HTML (safer and cleaner parsing than MarkdownV2, preventing crash loops on arbitrary special characters in company names or packages).
- **D-13:** Alerts must be visually styled with bold headers, custom priority emoji badges (🔴 Offer, 🟡 Shortlist, 🔵 Interview, 🟢 Assessment, ⚪ Opportunity), and metadata tables.
- **D-14:** Telegram notifications must *always* be delivered silently (`disable_notification=True` in the API call) to prevent student distraction.

### Deterministic Local Pre-Check Rules
- **D-15:** Run exact case-insensitive substring search in the email body for Register Numbers, NeoPAT IDs, and Emails. For Names, split the student's name into tokens and require at least two name tokens to match (avoiding middle-name or format mismatches).
- **D-16:** If no student identifiers are matched in the body by the pre-check, still proceed to Gemini AI classification (the email might be a batch-wide opportunity or the student might be shortlisted in an attachment scanned in Phase 3).

### AI Gateway Rate Limiting & Retry Backoffs
- **D-17:** Implement a Redis-based token bucket rate limiter to prevent multiple Celery tasks from concurrently hitting Gemini 429 rate limits, delaying execution of tasks when quotas are exceeded.
- **D-18:** Store prompt templates in YAML files inside the codebase (under `src/core/prompts/`), versioned by filename or keys, and log the active version in usage tables.
- **D-19:** The `ai_usage_logs` database schema must include: `id` (PK), `model_name` (str), `prompt_version` (str), `input_tokens` (int), `output_tokens` (int), `estimated_cost_usd` (numeric), `message_id` (str), `status` (str), and `created_at` (timestamp).

### the agent's Discretion
- Redis rate-limiter bucket size limits and exact key namespace formatting.
- Precise layout details of the Telegram HTML message structure.
- Details of the local rule-based parsing engine fallback parser logic.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- [PROJECT.md](file:///.planning/PROJECT.md) — Core value, constraints, and architecture diagram
- [REQUIREMENTS.md](file:///.planning/REQUIREMENTS.md) — Traceability mapping and v1 requirements (`PROC-01` to `PROC-08`)
- [ROADMAP.md](file:///.planning/ROADMAP.md) — Phase 2 scope boundaries and success criteria
- [01-CONTEXT.md](file:///.planning/phases/01-ingestion-security-foundation/01-CONTEXT.md) — Phase 1 context and credential security boundaries

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- [security.py](file:///d:/projects/PlacementBot/src/core/security.py) § `CredentialEncryptor` — Decrypt Gmail refresh tokens out-of-band in Celery workers to connect to the Gmail API.
- [config.py](file:///d:/projects/PlacementBot/src/core/config.py) — Add Google Gemini API keys and Telegram Bot credentials.

### Established Patterns
- FastAPI dependency injection and async/sync separation for database operations.
- Pypest testing suite with SQLite in-memory engine patching in `conftest.py`.

### Integration Points
- Celery worker task `process_email_event` in [email_tasks.py](file:///d:/projects/PlacementBot/src/tasks/email_tasks.py) is triggered by the webhook. This task will retrieve the email, run pre-checks, execute the AI Gateway, and dispatch Telegram notifications.

</code_context>

<specifics>
## Specific Ideas

- Always use `disable_notification=True` when invoking the Telegram Bot send message API.
- Emojis per priority: 🔴 Offer, 🟡 Shortlist, 🔵 Interview, 🟢 Assessment, ⚪ Opportunity.

</specifics>

<deferred>
## Deferred Ideas

- Model fallback to `gemini-1.5-flash` — deferred in favor of rule-based deterministic parsing and generic notification routing.
- Interactive bot features (status checks, registration updates, pause/mute commands) — deferred to CHAT-01/CHAT-02 (v2 requirements).

</deferred>

---

*Phase: 02-core-processing-ai-gateway-telegram-bot*
*Context gathered: 2026-06-09*
