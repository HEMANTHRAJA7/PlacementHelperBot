# Feature Landscape

**Domain:** Real-time Placement Notification System
**Researched:** 2026-06-08

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Gmail OAuth2 Connection | Securely links the student's Gmail account and stores a refresh token. | Medium | Uses Google's standard OAuth2 workflow. |
| Gmail API Watch (Pub/Sub) | Receives real-time push events from Gmail for new emails instead of polling. | Medium | Requires background renewal task since watches expire in 7 days. |
| Secure Webhook Endpoint | Listens to Google Pub/Sub push messages and validates their origin. | High | Must verify Google Cloud OIDC tokens for JWT authenticity. |
| Celery Async Worker Processing | Decouples webhook receipt from heavy tasks like API fetching and AI classification. | Medium | Crucial to avoid webhook timeouts (needs to return HTTP 200 within seconds). |
| Regex / Name Matching | Checks the email body and subject for basic student identifiers (Register Number, NeoPAT ID, Name). | Low | Fast, low cost, completely deterministic backup. |
| Telegram Notification Bot | Sends structured alerts to the user containing company, event type, and action links. | Low | Uses standard Telegram bot API client. |

## Differentiators

Features that set product apart. Not expected, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Gemini Vision OCR & Parsing | Direct analysis of Excel sheets, PDFs, and image screenshots of shortlists using multimodal LLM. | High | Skips complex and error-prone local OCR pipelines. |
| Structured AI Classification | Automatically categorizes email type (PLACEMENT_OPPORTUNITY, INTERNSHIP, ASSESSMENT, SHORTLIST, etc.). | Medium | Uses Gemini's Pydantic response schema to avoid JSON parse errors. |
| Field-Level AES-256 Encryption | Protects Gmail refresh tokens and student IDs in the Postgres database. | Medium | Managed using a master key in env vars. |
| Automatic Data Destruction | Temporary files/attachments are deleted immediately after parsing. | Medium | Zero permanent attachment storage on server. |
| Deadline Reminders | Automatically schedules secondary Telegram alerts 24h, 6h, and 1h before parsed deadlines. | High | Relies on Celery beat or Redis TTL-based notification schedules. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Resume Analyzer | Out of scope, introduces high token usage and complicates core notification focus. | Advise user to use standard external tools; focus purely on email ingestion. |
| Job Recommendation System | Bloats the codebase with complex recommendation engines that don't fit real-time notifications. | Notify on ALL incoming placement emails; let students filter opportunities. |
| Interactive Conversational Telegram Bot | Increases complexity of bot design, state management, and user interaction. | Bot is unidirectional (push-only). Telegram bot receives alerts via webhook/POST endpoint. |
| Multi-College Support | Scoping for different email formats and college portals is too broad for an MVP. | Focus exclusively on VIT email templates, registration number format (`[0-9]{2}[A-Z]{3}[0-9]{4}`), and NeoPAT IDs. |

## Feature Dependencies

```
[Gmail OAuth2 Setup] -> [Gmail API Watch Registration] -> [Pub/Sub Webhook Listener]
                                                                  |
                                                                  v
[AI Classification & Metadata Extraction] <----------- [Celery Queue Ingestion]
                |
                v
[Gemini Vision Attachment Processing] -> [Candidate Matching Engine] -> [Telegram Bot Push]
                                                                             |
                                                                             v
                                                                  [Intelligent Reminders]
```

## MVP Recommendation

Prioritize:
1. **Gmail OAuth & Real-time Webhook Ingestion**: Complete authentication loop, Pub/Sub webhook setup, event caching, and basic email body retrieval.
2. **AI Email Classifier & Candidate Matching**: Setup Gemini Flash schema validation to categorize incoming mails and search for student identifiers in email body.
3. **Multimodal Attachment Scanning**: Ingest PDFs, Excels, and images into Gemini Vision to detect user identifiers.
4. **Telegram Bot & Security Polish**: Deploy push notifications to Telegram, implement AES-256 DB encryption, Pub/Sub JWT validation, and clean up local temp files.

Defer:
- **Intelligent Reminder Scheduler**: Implement in a secondary phase after core delivery, as scheduling requires durable celery beat scheduling or a dedicated Redis key eviction listener.

## Sources
- Google OAuth API docs: https://developers.google.com/identity/protocols/oauth2
- Gemini Multimodal capabilities: https://ai.google.dev/gemini-api/docs/multimodal
