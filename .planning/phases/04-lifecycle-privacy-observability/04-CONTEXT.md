# Phase 4: Lifecycle, Privacy, & Observability - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers system maintenance, data privacy, and telemetry capabilities:
1. Daily automatic renewal of Gmail Watch API subscriptions via Celery Beat, with robust retry logic.
2. Metadata-only structured database audit logging to track onboarding, renewals, notifications, and errors, with a 90-day retention cleanup loop.
3. Telemetry and metrics exposure via a GET `/metrics` Prometheus-compatible endpoint.
4. Detailed health checks via a JSON GET `/api/v1/health` endpoint.

</domain>

<decisions>
## Implementation Decisions

### Gmail Watch Renewal & Lifecycle
- **D-30:** A scheduled daily Celery task will loop through all users in the database and renew their Gmail Watch subscriptions.
- **D-31:** **Watch Retry & Failure Policy:** If a watch renewal fails, the task will retry 3 times with exponential backoff. If all retries fail, it will flag the user's status as inactive (`watch_active = False`) and send a silent Telegram notification warning the user that their connection has expired and they need to re-authenticate.

### Structured Audit Logging (Privacy-First)
- **D-32:** **Metadata-Only Rule:** Audit logs must contain metadata only. It is strictly forbidden to store email subjects, email bodies, attachment filenames, OCR outputs, Gemini prompts, Gemini responses, company names, student identifiers, or shortlist contents.
- **D-33:** **AuditLog Schema:** The `AuditLog` table will use structured columns rather than free-form text:
  - `id` (PK)
  - `user_id` (FK to users)
  - `event_type` (e.g., `"watch_renew"`, `"notification"`, `"onboarding"`, `"dlq_routing"`)
  - `status` (e.g., `"success"`, `"failed"`)
  - `message_id` (Gmail identifier, optional)
  - `resource_type` (e.g., `"gmail_api"`, `"telegram_api"`, `"ai_gateway"`, `"database"`)
  - `error_code` (Standardized error tags, nullable)
  - `retry_count` (integer, default=0)
  - `created_at` (timestamp)
- **D-34:** **Data Retention:** Audit logs and DLQ logs will enforce a strict 90-day retention period. A daily Celery task will automatically delete records older than 90 days.

### Observability & Metrics
- **D-35:** **Prometheus Metrics:** We will expose a GET `/metrics` endpoint using the `prometheus-client` package with the following metrics:
  - `active_watches_total` (Gauge: healthy vs expired)
  - `ai_cost_usd_total` (Counter: total money spent on Gemini API)
  - `ai_tokens_total` (Counter: prompt and generation tokens, labeled by model)
  - `notifications_sent_total` (Counter: notifications sent, labeled by category)
  - `dlq_failures_total` (Counter: items written to Dead Letter Queue)
  - `gmail_events_processed_total` (Counter: incoming unique push events processed)
  - `gmail_duplicate_events_total` (Counter: incoming duplicate push events dropped)
  - `ai_failures_total` (Counter: failed AI Gateway requests)
  - `telegram_delivery_failures_total` (Counter: failed Telegram API calls)
  - `attachment_parse_failures_total` (Counter: failed PDF/Excel/OCR extractions)
  - `attachment_matches_total` (Counter: matches found in attachments)
  - `celery_pending_tasks_total` (Gauge/Counter: pending/active tasks in queue)
  - `gmail_watch_renew_failures_total` (Counter: failed daily watch renewals)
- **D-36:** **Health Checks:** We will expose a GET `/api/v1/health` JSON endpoint that actively validates:
  - PostgreSQL connectivity (running a simple test query).
  - Redis connectivity (running a ping command).
  - Celery worker heartbeat (verifying that at least one background worker is active).
  - Gmail watch renewal service health (verifying that watch renewals have run successfully in the last 24 hours).

</decisions>

<canonical_refs>
## Canonical References

### Project Scope & Guidelines
- [ROADMAP.md](file:///.planning/ROADMAP.md) — Contains the goals and success criteria for Phase 4.
- [GEMINI.md](file:///GEMINI.md) — Standardizes security, privacy, data retention, and OIDC Oauth validation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- [database.py](file:///src/core/database.py) & [worker.py](file:///src/tasks/worker.py): Setup points for DB and Celery references.
- [email_tasks.py](file:///src/tasks/email_tasks.py): Background task loops where metrics can be incremented.
- [AIGateway](file:///src/core/ai_gateway.py): Logging usage method can hook into AI cost metrics.

### Integration Points
- **Health Checks & Telemetry Routing:** We will register GET `/metrics` and GET `/api/v1/health` in our FastAPI app at [main.py](file:///src/main.py) or in a new endpoints router module.

</code_context>

<deferred>
## Deferred Ideas
- None.

</deferred>

---

*Phase: 4-Lifecycle, Privacy, & Observability*
*Context gathered: 2026-06-10*
