# Placement Sentinel

## What This Is

Placement Sentinel is a secure, AI-powered placement notification system designed specifically for VIT students (2027 Batch). The system acts as a secondary notification layer between Gmail and Telegram, watching incoming emails to intelligently identify placement-related content, scan attachments, detect whether the student is personally shortlisted, and send high-priority Telegram notifications.

## Core Value

Ensure students never miss critical placement emails, shortlist updates, interview schedules, deadlines, assessments, or offer notifications, while strictly maintaining security and privacy.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Implement Gmail Watch API to register push notifications for incoming emails.
- [ ] Use Google Cloud Pub/Sub as the real-time event source for incoming email notifications.
- [ ] Create a webhook subscriber service (FastAPI) to validate Pub/Sub push messages via Google OIDC JWT signatures.
- [ ] Secure student secrets (OAuth refresh tokens, Register Numbers, NeoPAT IDs) using AES-256 encryption at rest with an environment-configured master key.
- [ ] Push raw ingestion events into Redis/Celery queue for asynchronous processing, complete with retry logic and Dead Letter Queue (DLQ) handling.
- [ ] Decouple downstream services from Gmail (process emails from cache/message store).
- [ ] Implement Redis-based event idempotency checking using email message ID hashes to avoid duplicates.
- [ ] Classify incoming emails using Gemini Flash into structured categories (PLACEMENT_OPPORTUNITY, INTERNSHIP, ASSESSMENT, SHORTLIST, INTERVIEW, OFFER, REJECTION, OTHER).
- [ ] Centralize all Gemini interactions in an AI Gateway Layer enforcing JSON schema validation, prompt versioning, cost tracking, retries, and rate limiting.
- [ ] Parse Excel, PDF, and image attachments using a hybrid processing architecture: try local python parsers (pandas/openpyxl, pdfplumber, OCR) first, falling back to Gemini Vision API only when deterministic parsing fails.
- [ ] Send structured Telegram notifications with concise message templates corresponding to notification categories sorted by a Priority Engine (Offer > Shortlist > Interview > Assessment > Opportunity).
- [ ] Enforce Principle of Least Privilege: request read-only permissions for Gmail API.
- [ ] Minimize data footprint: automatically destroy attachments immediately after processing (zero permanent storage).
- [ ] Set up daily background task to renew the Gmail Watch subscription.
- [ ] Implement observability (structured JSON logging, Prometheus metrics, security audit logs with metadata-only storage, and health checks).
- [ ] Set up intelligent reminders (24h, 6h, 1h, urgent) for upcoming deadlines based on priority.

### Out of Scope

- Resume analyzer — out of scope to focus strictly on real-time notifications.
- Job recommendation system — out of scope to avoid unnecessary complexity.
- Interactive Chatbot — out of scope as Placement Sentinel is primarily push-notification-based.
- Social features — out of scope to preserve student privacy.
- Multi-college support — out of scope to focus on VIT-specific identifiers and email patterns.

## Context

- VIT placement notifications are sent frequently to student inbox, but are easily missed due to high email volume or nested attachments.
- Scale: Initial deployment is personal use and small-scale trusted friends (5-50 users). The architecture should scale easily.
- Reliability, low-overhead, and high-security (handling sensitive student details) are critical for a portfolio-grade project.

## Constraints

- **Tech Stack**: FastAPI (Backend), PostgreSQL (Database), Redis (Cache/Queue), Celery (Workers), Gemini Flash API (AI), Telegram Bot API (Notifications), Docker, Railway (Deployment).
- **Least Privilege**: Only request read-only Gmail access scopes (`https://www.googleapis.com/auth/gmail.readonly`).
- **Data Retention**: Do not store email bodies or attachment binaries long-term. Delete attachments immediately after ingestion/processing.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Google Cloud Pub/Sub Ingestion | Enables real-time event-driven ingestion instead of polling, saving API quota and reducing latency. | — Pending |
| Hybrid Attachment Parsing | Uses fast, deterministic local libraries (pandas/pdfplumber) first, invoking Gemini Vision only as a fallback to control API costs. | — Pending |
| Security-First Phase ordering | Implements AES-256 DB encryption and OIDC webhook signature validation in Phase 1 before storing any credentials. | — Pending |
| Telegram Bot in Phase 2 | Shifts notification capability early in the lifecycle to deliver an end-to-end MVP by the end of Phase 2. | — Pending |
| Centralized AI Gateway | Controls LLM rate limits, cost metrics, prompt templates, and retries in a single cohesive backend layer. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-08 after initial definition*
