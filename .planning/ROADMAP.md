# Roadmap: Placement Sentinel

## Overview

Placement Sentinel is built sequentially across 5 MVP-style phases, delivering end-to-end value early by coupling ingestion with security in Phase 1, followed immediately by email classification and Telegram bot notifications in Phase 2. Phase 3 implements hybrid attachment parsing (deterministic local parsers with Gemini Vision fallback), Phase 4 focuses on watch lifecycle, privacy minimization, and observability, and Phase 5 introduces scheduled reminders.

## Phases

- [x] **Phase 1: Ingestion & Security Foundation** - Setup linked Gmail OAuth accounts, OIDC Pub/Sub webhooks, AES-256 DB encryption, and Celery DLQ queue.
- [x] **Phase 2: Core Processing, AI Gateway, & Telegram Bot** - Fetch mail, build AI Gateway with Gemini Flash classification, and send formatted priority alerts to Telegram.
- [x] **Phase 3: Hybrid Attachment Scanning & Matching** - Parse Excel, PDF, and Images deterministically, falling back to Gemini Vision for complex table matching.
- [x] **Phase 4: Lifecycle, Privacy, & Observability** - Implement Watch renewal, data minimization file wipes, audit logs, and Prometheus metrics.
- [x] **Phase 5: Reminder Engine** - Add scheduled Celery Beat reminders 24h, 6h, and 1h prior to application and interview deadlines.

## Phase Details

### Phase 1: Ingestion & Security Foundation
**Goal**: Setup linked Gmail OAuth accounts, OIDC Pub/Sub webhooks, AES-256 DB encryption, and Celery DLQ queue.
**Mode**: mvp
**Depends on**: Nothing
**Requirements**: INGST-01, INGST-02, INGST-03, INGST-04, INGST-05, INGST-06, SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. User can successfully complete Gmail OAuth2 flow and link account.
  2. Database credentials (refresh tokens, student IDs) are encrypted at rest using AES-256.
  3. Webhook listener verifies incoming Google Pub/Sub OIDC JWT signatures.
  4. Webhook enqueues events to Celery, and duplicate events are ignored via Redis idempotency keys.
  5. Celery tasks retry on failure and route persistent errors to a Dead-Letter Queue (DLQ).
**Plans**: 3 plans

Plans:
- [ ] 01-01: Initialize environment (Docker, DB models, migrations, FastAPI, AES-256 cryptography engine)
- [ ] 01-02: Implement Google OAuth2 Linkage, OIDC Webhook Validation, and encrypted credential storage
- [ ] 01-03: Implement Pub/Sub Webhook, Celery Queue Ingestion, Redis Idempotency, and DLQ Retry infrastructure

### Phase 2: Core Processing, AI Gateway, & Telegram Bot
**Goal**: Fetch mail, build AI Gateway with Gemini Flash classification, and send formatted priority alerts to Telegram.
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04, PROC-05, PROC-06, PROC-07, PROC-08
**Success Criteria** (what must be TRUE):
  1. Celery worker retrieves email body and metadata via Gmail API.
  2. Local pre-checks search for student ID patterns deterministically to skip LLM calls when possible.
  3. Centralized AI Gateway handles prompt versions, schema validations, retries, rate limits, and cost tracking.
  4. AI Gateway classifies email type and extracts metadata in validated Pydantic JSON formats.
  5. Telegram Bot pushes formatted alerts sorted by Priority Engine (Offer > Shortlist > Interview > Assessment > Opportunity).
**Plans**: 3 plans

Plans:
- [ ] 02-01: Implement background Gmail mail retrieval service and local deterministic pre-check
- [ ] 02-02: Build Centralized AI Gateway for Gemini Flash Pydantic integration, cost tracking, prompt versioning, rate limiting, and retries
- [ ] 02-03: Implement Telegram Bot dispatcher and Priority Engine (Offer > Shortlist > Interview > Assessment > Opportunity)

### Phase 3: Hybrid Attachment Scanning & Matching
**Goal**: Parse Excel, PDF, and Images deterministically, falling back to Gemini Vision for complex table matching.
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: MATCH-01, MATCH-02, MATCH-03, MATCH-04
**Success Criteria** (what must be TRUE):
  1. Excel sheets parsed deterministically using pandas/openpyxl and searched for user identifiers.
  2. PDFs parsed deterministically using pdfplumber and searched for user details.
  3. Images parsed using local OCR engines to detect candidate matching text.
  4. Gemini Vision API executes only as a fallback when local deterministic text extraction fails.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Implement local deterministic PDF, Excel, and Image OCR loaders with candidate matching rules
- [ ] 03-02: Implement Gemini Vision fallback logic for failsafe document/table parsing and integrate with matching engine

### Phase 4: Lifecycle, Privacy, & Observability
**Goal**: Implement Watch renewal, data minimization file wipes, audit logs, and Prometheus metrics.
**Mode**: mvp
**Depends on**: Phase 3
**Requirements**: INGST-07, INGST-08, SEC-03, SEC-04, SEC-05
**Success Criteria** (what must be TRUE):
  1. Background Celery task renews Gmail Watch subscriptions daily and monitors health.
  2. Temporary files and attachments are immediately wiped after processing (Data Minimization).
  3. Security audit logs track OAuth actions, watch renewals, email logs, and notifications with metadata-only storage.
  4. Prometheus metrics and health check endpoints expose worker queue lag, watch statuses, and AI costs.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Implement daily Gmail Watch renewal task and status monitoring dashboard
- [ ] 04-02: Enforce Data Minimization (wipe attachments/email caches) and construct metadata-only Security Audit Logging
- [ ] 04-03: Set up structured JSON logging, health checks, and Prometheus metrics

### Phase 5: Reminder Engine
**Goal**: Add scheduled Celery Beat reminders 24h, 6h, and 1h prior to application and interview deadlines.
**Mode**: mvp
**Depends on**: Phase 4
**Requirements**: REM-01
**Success Criteria** (what must be TRUE):
  1. Celery Beat handles event scheduling and schedules reminders 24h, 6h, and 1h prior to deadlines.
  2. Notifications are pushed to Telegram based on priority-based reminder policies.
**Plans**: 1 plans

Plans:
- [ ] 05-01: Build scheduled deadline reminder tracking database models and Celery Beat scheduler

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ingestion & Security Foundation | 3/3 | Completed | 2026-06-09 |
| 2. Core Processing, AI Gateway, & Telegram Bot | 3/3 | Completed | 2026-06-09 |
| 3. Hybrid Attachment Scanning & Matching | 2/2 | Completed | 2026-06-10 |
| 4. Lifecycle, Privacy, & Observability | 3/3 | Completed | 2026-06-10 |
| 5. Reminder Engine | 1/1 | Completed | 2026-06-10 |
