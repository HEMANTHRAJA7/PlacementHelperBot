# Requirements: Placement Sentinel

**Defined:** 2026-06-08
**Core Value:** Ensure VIT students never miss critical placement updates through secure, real-time AI-powered Telegram notifications, with zero persistent storage of sensitive email content.

## v1 Requirements

### Ingestion (INGST)

- [ ] **INGST-01**: User can authenticate via Gmail OAuth2 and link their VIT student account.
- [ ] **INGST-02**: System registers a Gmail Watch API subscription for the linked mailbox.
- [ ] **INGST-03**: FastAPI Webhook endpoint captures push notifications from Google Cloud Pub/Sub.
- [ ] **INGST-04**: Webhook endpoint immediately enqueues raw mailbox events into Redis/Celery queue.
- [ ] **INGST-05**: System uses Redis keys to verify event idempotency, ignoring duplicate Pub/Sub messages.
- [ ] **INGST-06**: Celery workers implement retry mechanisms with exponential backoff and route failed jobs to a Dead-Letter Queue (DLQ).
- [ ] **INGST-07**: Background task automatically renews the Gmail Watch subscription daily.
- [ ] **INGST-08**: System monitors Gmail Watch status and logs alerts for watches nearing expiration.

### Processing & AI (PROC)

- [ ] **PROC-01**: Celery worker retrieves email body, subject, and attachments via Gmail API in the background.
- [ ] **PROC-02**: System runs a local deterministic pre-check on email text for student identifiers (Register Number, NeoPAT ID, Email, Name) before calling LLM.
- [ ] **PROC-03**: Centralized AI Gateway parses email using Gemini Flash, returning structured JSON matching a Pydantic schema.
- [ ] **PROC-04**: AI Gateway classifies email type (PLACEMENT_OPPORTUNITY, INTERNSHIP, ASSESSMENT, SHORTLIST, INTERVIEW, OFFER, REJECTION, OTHER).
- [ ] **PROC-05**: AI Gateway extracts metadata (Company Name, Role, Package, Deadline, Event Type, Application Link).
- [ ] **PROC-06**: AI Gateway processes attachments (PDFs, Excel sheets, and Images) using Gemini Vision to find candidate shortlist status.
- [ ] **PROC-07**: AI Gateway logs cost metrics, enforces rate limits, handles retries, and maintains prompt versions.

### Notification & Reminders (NOTF)

- [ ] **NOTF-01**: Telegram Bot sends structured markdown notifications with direct action links.
- [ ] **NOTF-02**: Notifications are styled by priority level (Offer > Shortlist > Interview > Assessment > Opportunity).
- [ ] **NOTF-03**: Scheduler sends automated alerts 24h, 6h, and 1h prior to parsed application or event deadlines.

### Security & Privacy (SEC)

- [ ] **SEC-01**: Webhook listener validates incoming Pub/Sub HTTP POST request using Google OIDC JWT signatures.
- [ ] **SEC-02**: DB fields (OAuth refresh tokens, Register Numbers, NeoPAT IDs) are encrypted at rest using AES-256 (cryptography Fernet) with a master key.
- [ ] **SEC-03**: Temporary email attachments are processed entirely in memory or temporary volumes and deleted immediately upon task completion.
- [ ] **SEC-04**: System generates security audit logs tracking OAuth events, watch renewals, email processing, and notification delivery, storing metadata only.
- [ ] **SEC-05**: Observability setup implements structured JSON logging, health checks, and Prometheus metrics.

## v2 Requirements

### Interactive Chatbot (CHAT)

- **CHAT-01**: Telegram Bot accepts interactive commands for status checks, registration updates, and history review.
- **CHAT-02**: User can pause or mute notifications directly from Telegram.

### Analytics (ANLT)

- **ANLT-01**: User dashboard displays success rates, statistics, and a timeline of placements.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Resume Analyzer | High token complexity and unnecessary for email alert priority. |
| Job Recommendation System | Excluded to keep the notification engine simple and focused. |
| Social Features | Kept out to maintain privacy for students' personal placement outcomes. |
| Multi-College Support | Avoids template bloat; focused solely on VIT email formats and student IDs. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGST-01 | Phase 1 | Pending |
| INGST-02 | Phase 1 | Pending |
| INGST-03 | Phase 1 | Pending |
| INGST-04 | Phase 1 | Pending |
| INGST-05 | Phase 1 | Pending |
| INGST-06 | Phase 1 | Pending |
| INGST-07 | Phase 4 | Pending |
| INGST-08 | Phase 4 | Pending |
| PROC-01 | Phase 2 | Pending |
| PROC-02 | Phase 2 | Pending |
| PROC-03 | Phase 2 | Pending |
| PROC-04 | Phase 2 | Pending |
| PROC-05 | Phase 3 | Pending |
| PROC-06 | Phase 3 | Pending |
| PROC-07 | Phase 2 | Pending |
| NOTF-01 | Phase 4 | Pending |
| NOTF-02 | Phase 4 | Pending |
| NOTF-03 | Phase 5 | Pending |
| SEC-01 | Phase 4 | Pending |
| SEC-02 | Phase 4 | Pending |
| SEC-03 | Phase 4 | Pending |
| SEC-04 | Phase 4 | Pending |
| SEC-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-08*
*Last updated: 2026-06-08 after initial definition*
