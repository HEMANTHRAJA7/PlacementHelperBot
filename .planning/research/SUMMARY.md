# Research Summary: Placement Sentinel

**Domain:** Secure Email Notification & AI-Parsing Systems
**Researched:** 2026-06-08
**Overall confidence:** HIGH

## Executive Summary

Placement Sentinel watches incoming Gmail accounts of VIT students, uses Gemini 2.0 Flash to classify emails, processes attachments (Excel, PDF, Images) to find shortlist status, and alerts users via Telegram. 

Research focuses on building a secure, reliable, and decoupled pipeline. Google Pub/Sub push webhooks verified via OIDC JWT provide real-time notification with low overhead. An asynchronous task worker architecture (Redis + Celery) isolates FastAPI from long-running operations. Gemini Flash handles structured JSON schema classification and multimodal attachment reasoning natively. Field-level database encryption using AES-256 (via cryptography libraries) ensures user credentials (refresh tokens, student IDs) are secure at rest. 

The biggest challenge is Gmail watch's 7-day expiration, which requires a robust daily renewal daemon.

## Key Findings

- **Stack:** FastAPI, PostgreSQL, Redis, Celery, google-genai SDK, and cryptography (AES-256).
- **Architecture:** Decoupled Pub/Sub Webhook ingress pushing to Celery for worker-based fetching, Gemini parsing, and Telegram notification.
- **Critical Pitfall:** Gmail API Watch subscriptions silently expire after 7 days; resolved via automatic daily Celery Beat renewal tasks.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Ingestion & Webhook Infrastructure**
   - Goal: Authenticate users, register Gmail Watch, and receive push notifications in a background queue.
   - Addresses: OAuth2, Pub/Sub webhook endpoint, Celery & Redis pipeline setup, database schema.
   - Avoids: Webhook timeouts by immediately queuing events.

2. **Phase 2: Core Processing & Classification**
   - Goal: Fetch email contents, classify message categories, and extract opportunity details.
   - Addresses: Gmail API content fetching, Gemini Flash JSON schema classification, and metadata extraction.
   - Avoids: Brittle string matching by using structured JSON schemas via Pydantic.

3. **Phase 3: Attachment OCR & Shortlist Detection**
   - Goal: Extract student lists from Excel, PDF, and image attachments, matching user identifiers.
   - Addresses: Local file loaders, Gemini Vision parsing, and candidate matching rules.
   - Avoids: OCR false negatives through double-validation and formatting normalizations.

4. **Phase 4: Notification Delivery & Security Polish**
   - Goal: Send Telegram bot messages, encrypt credentials at rest, and validate Pub/Sub signatures.
   - Addresses: Telegram Bot client, AES-256 DB encryption, Pub/Sub JWT validation, and files cleanup.
   - Avoids: Data leaks and unauthorized webhooks.

5. **Phase 5: Scheduling & Reminders (Optional Portfolio Boost)**
   - Goal: Schedule automated notifications 24h, 6h, and 1h prior to application deadlines.
   - Addresses: Celery Beat event scheduling, reminder state database tracking.
   - Avoids: Missed deadlines by tracking expired schedules.

**Phase ordering rationale:**
- Ingestion and queue foundation must come first, as they govern how data enters the system. Core classification can then run on raw emails, followed by attachment processing which adds heavy AI/multimodal computation. Notification and security layer are built on top, with reminders added last.

**Research flags for phases:**
- Phase 1: Needs GCP OAuth consent screen configuration research.
- Phase 3: Multimodal file input limits and token optimization.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Standard python stack (FastAPI, Redis, Postgres, Celery) works flawlessly on Railway. |
| Features | HIGH | Table stakes and differentiators are well documented and within API limits. |
| Architecture | HIGH | Decoupled architecture prevents webhook timeouts and scaling bottlenecks. |
| Pitfalls | HIGH | Solved the core pitfalls (expiration, retries, encryption) with documented engineering patterns. |

## Gaps to Address

- **GCP Pub/Sub Setup Documentation**: Must write clear instructions for GCP Console configuration, granting publisher permissions to Gmail, and OIDC setup.
- **Gemini Vision Payload Limits**: Determine max size limits for passing multiple PDFs/Excel sheets to Gemini Vision API and define fallback local chunking strategies.
- **Local Dev vs Prod Webhook Routing**: Since local dev environment is behind NAT, ngrok/localtunnel must be configured to receive Google Pub/Sub push messages.
