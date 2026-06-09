# Walking Skeleton — Placement Sentinel

**Phase:** 1
**Generated:** 2026-06-09

## Capability Proven End-to-End

A student can request a login link from the Telegram Bot, complete the Google OAuth authorization flow in their browser, and see a callback redirect success page, resulting in their Gmail refresh token being safely encrypted via AES-256 and stored in PostgreSQL.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | FastAPI + Uvicorn | Lightweight, high-performance async framework with automatic Swagger documentation. |
| Data layer | PostgreSQL + SQLAlchemy | Relational DB with robust transactional support for user metadata and audit logs, using SQLAlchemy async ORM. |
| Cryptography | AES-256 Fernet (`cryptography`) | Cryptographically authenticated symmetric encryption for securely storing user secrets at rest. |
| Task Ingestion | Redis + Celery | Decouples webhook POST execution from long-running Gmail downloads and AI reasoning. |
| Directory layout | Structured Layered Folders | Separation of concerns: `src/core` (config/db), `src/models` (entities), `src/api` (routes), `src/tasks` (celery workers). |

## Stack Touched in Phase 1

- [ ] Project scaffold (FastAPI boilerplate, Dockerfile, Docker Compose, test suite config)
- [ ] Routing — `/api/v1/auth/login` and `/api/v1/auth/callback` endpoints, and a Pub/Sub webhook `/api/v1/webhook`
- [ ] Database — PostgreSQL table schema for `users` (write encrypted credentials and read Telegram mappings)
- [ ] Security — OIDC signature checking on webhooks and AES-256 Fernet column encryption
- [ ] Ingest queue — Redis queueing and Celery background task worker stubs
- [ ] Deployment — local Docker Compose stack running PostgreSQL, Redis, FastAPI, and Celery worker

## Out of Scope (Deferred to Later Slices)

- Email metadata extraction and AI classification (deferred to Phase 2)
- Real-time Telegram bot push notification dispatch (deferred to Phase 2)
- PDF/Excel/Image attachment matching (deferred to Phase 3)
- Daily Watch renewal daemon (deferred to Phase 4)
- Scheduled deadline reminders (deferred to Phase 5)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: Core Processing, AI Gateway, & Telegram Bot (classification + delivery)
- Phase 3: Hybrid Attachment Scanning & Matching (PDF, Excel, Images + fallback AI)
- Phase 4: Lifecycle, Privacy, & Observability (auto-renewal, log wipes, metrics)
- Phase 5: Reminder Engine (scheduled alerts)
