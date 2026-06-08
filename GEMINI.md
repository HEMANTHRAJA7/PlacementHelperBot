<!-- GSD:project-start source:PROJECT.md -->

## Project

**Placement Sentinel**

Placement Sentinel is a secure, AI-powered placement notification system designed specifically for VIT students (2027 Batch). The system acts as a secondary notification layer between Gmail and Telegram, watching incoming emails to intelligently identify placement-related content, scan attachments, detect whether the student is personally shortlisted, and send high-priority Telegram notifications.

**Core Value:** Ensure students never miss critical placement emails, shortlist updates, interview schedules, deadlines, assessments, or offer notifications, while strictly maintaining security and privacy.

### Constraints

- **Tech Stack**: FastAPI (Backend), PostgreSQL (Database), Redis (Cache/Queue), Celery (Workers), Gemini Flash API (AI), Telegram Bot API (Notifications), Docker, Railway (Deployment).
- **Least Privilege**: Only request read-only Gmail access scopes (`https://www.googleapis.com/auth/gmail.readonly`).
- **Data Retention**: Do not store email bodies or attachment binaries long-term. Delete attachments immediately after ingestion/processing.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | ^0.111.0 | Web Application / Webhook API | High performance async framework, automatic Swagger generation, excellent integration with Pydantic and OAuth2 flows. |
| Uvicorn | ^0.30.0 | ASGI Server | Lightning-fast ASGI web server implementation. |

### Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16 | Relational Database | Highly reliable, robust support for relational schemas (Users, Emails, Audit Logs), indexing, JSONB data types, and transactional safety. |
| SQLAlchemy | ^2.0.0 | Async ORM | Industry-standard Python ORM with full asyncio support. |
| Alembic | ^1.13.0 | Migration Tool | Handles declarative database schema evolution safely. |

### Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Redis | 7 | Cache & Message Broker | Fast in-memory key-value store, used as the message broker for Celery and for caching token statuses and idempotency keys. |
| Celery | ^5.4.0 | Distributed Task Queue | Handles background email scanning, attachment parsing, and notification retries asynchronously. |
| Docker & Compose | ^25.0 | Containerization | Standardizes environment across local development and production Railway deployment. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google-genai | ^0.1.0 | Official Google Gemini SDK | Pass emails and files directly to Gemini 2.0 Flash with native structured outputs. |
| cryptography | ^42.0 | AES-256 Encryption at Rest | Encrypt sensitive database fields (OAuth tokens, Register numbers) before DB write. |
| google-auth | ^2.29.0 | OAuth OIDC JWT Validation | Verifies incoming Pub/Sub OIDC JWT signatures to authenticate Google webhook requests. |
| PyPDF2 / pdfplumber | ^3.0 / ^0.11 | Backup local text extraction | Fast deterministic extraction of text from standard PDFs before handing over to LLM. |
| openpyxl | ^3.1 | Excel Sheet parsing | Extracts cells from Excel sheets deterministically to scan for student IDs. |
| httpx | ^0.27.0 | Async HTTP Client | Non-blocking API requests to Telegram Bot API and other external services. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| AI SDK | `google-genai` | `langchain` | Langchain introduces significant abstraction overhead and latency, whereas the direct SDK is lightweight, fast, and supports `.parsed` Pydantic models directly. |
| Task Queue | `Celery` | `ARQ` / `Dramatiq` | Celery has broader ecosystem support, mature retry configurations, dead-letter monitoring, and is easier to integrate with PostgreSQL/Redis in standard portfolio architectures. |
| Image OCR | `Gemini Vision` | `Tesseract OCR` | Tesseract requires installing heavy native system binaries in Docker, struggles with multi-column tables, and has poor accuracy on blurry mobile screenshots. Gemini Flash processes images/PDFs natively in a single API call. |

## Installation

# Core Dependencies

# Dev & Test Dependencies

## Sources

- FastAPI Official Docs: https://fastapi.tiangolo.com/
- Google GenAI SDK: https://github.com/googleapis/python-genai
- Google Pub/Sub Webhook JWT Authentication: https://cloud.google.com/pubsub/docs/push
- Celery Task Queue: https://docs.celeryq.dev/

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agent/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
