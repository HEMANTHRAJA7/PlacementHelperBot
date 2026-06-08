# Technology Stack

**Project:** Placement Sentinel
**Researched:** 2026-06-08

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

```bash
# Core Dependencies
pip install fastapi uvicorn sqlalchemy asyncpg alembic redis celery google-genai cryptography google-auth openpyxl pdfplumber httpx pydantic-settings

# Dev & Test Dependencies
pip install pytest pytest-asyncio black flake8 httpx
```

## Sources
- FastAPI Official Docs: https://fastapi.tiangolo.com/
- Google GenAI SDK: https://github.com/googleapis/python-genai
- Google Pub/Sub Webhook JWT Authentication: https://cloud.google.com/pubsub/docs/push
- Celery Task Queue: https://docs.celeryq.dev/
