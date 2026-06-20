# Placement Sentinel ⏰🤖

Placement Sentinel is a secure, real-time, AI-powered recruitment notification and deadline reminder system designed for college students. It acts as an automated secondary notification layer between Google Gmail and Telegram, scanning incoming emails for placement updates, parsing attachments (PDFs, Excel sheets, and images), identifying whether the student is personally shortlisted, and delivering prioritized Telegram alerts and scheduled reminders.

> [!IMPORTANT]
> **Privacy First**: Placement Sentinel enforces a strict zero-persistent-storage policy for email bodies, attachments, and student identifiers. Security logs use metadata-only tracking, and DB values are encrypted at rest using AES-256.

---

## 🏗️ Architecture Overview

The system runs asynchronously using FastAPI, PostgreSQL, Redis, Celery workers, and Celery Beat.

```mermaid
graph TD
    A[Gmail Inbox] -->|Pub/Sub Push Event| B[FastAPI Webhook Router]
    B -->|Verify OIDC JWT Signature| C{Is Valid?}
    C -->|No| D[Reject Request]
    C -->|Yes & Verify Idempotency| E[Enqueue to Redis/Celery]
    E -->|Celery Worker| F[Fetch & Decrypt Tokens]
    F -->|Gmail API| G[Retrieve Email & Attachments]
    G -->|Memory-Only Processing| H[Local Deterministic Matcher]
    H -->|Match Fail / PDF/OCR/Excel Image| I[Gemini Vision Fallback]
    H & I -->|Student Matched?| J[Gemini 2.0 Flash Classifier]
    J -->|Categorize & Parse Deadline| K{Eligible Category?}
    K -->|Yes| L[Create Database Reminder]
    K -->|No/Yes| M[Telegram Bot Dispatcher]
    
    N[Celery Beat Scheduler] -->|Every 5 Min| O[Check Reminders Task]
    O -->|Evaluate Deadline/2h Catch-up| P[Send Alert 24h / 6h / 1h]
    P --> M
```

---

## ✨ Features

- **Secure Gmail Webhook Ingestion**: Receives instant notifications of new emails via Google Cloud Pub/Sub with OIDC JWT signature verification.
- **AES-256 Encryption at Rest**: Uses Cryptography Fernet to encrypt OAuth tokens, student registration numbers, and identifier codes in the PostgreSQL database.
- **Gemini 2.0 Flash Email Classifier**: Parses email text to output structured JSON matching a Pydantic schema, identifying placement updates, deadlines, roles, packages, and links.
- **Hybrid Attachment Scanner**:
  - Parses standard **PDFs** (`pdfplumber`) and **Excel sheets** (`openpyxl`) in memory.
  - Automatically runs local **OCR** (`pytesseract`) on image attachments.
  - Calls **Gemini Vision API** ONLY as a fallback for complex formatting or table structures.
- **Telegram Bot Priority Dispatcher**: Delivers prioritized placement notifications (`Offer > Shortlist > Interview > Assessment > Opportunity`) with normal sound priority settings.
- **Intelligent Reminder Engine**: Sends automated follow-up reminders at `24 hours`, `6 hours`, and `1 hour` before deadlines using a resilient `2-hour catch-up` policy.
- **Observability**: Exposes detailed Prometheus `/metrics` (cost, token usage, failures, queue sizes) and `/api/v1/health` status checking.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python ASGI)
- **Database**: PostgreSQL (SQLAlchemy Async ORM, Alembic migrations)
- **Queue/Cache**: Redis & Celery (Asynchronous Workers)
- **AI Engine**: Google GenAI SDK (Gemini 2.0 Flash)
- **Scheduler**: Celery Beat (Periodic task runner)
- **Metrics**: Prometheus client
- **Containerization**: Docker & Docker Compose

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- PostgreSQL & Redis (or Docker)
- Tesseract OCR (for image scanning)
  - *Windows*: Install Tesseract binaries and add to system Path.
  - *Mac/Linux*: Install via `brew install tesseract` or `apt-get install tesseract-ocr`.

### 1. Configure the Environment
Create a `.env` file in the root directory and configure the variables:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/placement_sentinel
REDIS_URL=redis://localhost:6379/0
AES_SECRET_KEY=  # Run generation command below

# Google OAuth2 Credentials (from GCP Console)
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback

# Google Pub/Sub Webhook Audience
WEBHOOK_AUDIENCE=http://localhost:8000/api/v1/webhook

# API Keys & Subscriptions
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GMAIL_PUBSUB_TOPIC=projects/your-gcp-project/topics/gmail-push
```

To generate your `AES_SECRET_KEY`, run:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Start Services via Docker
Start the Postgres and Redis databases:
```bash
docker-compose up -d
```

### 3. Run Database Migrations
Deploy the database schema using Alembic:
```bash
alembic upgrade head
```

### 4. Running the Application
Launch the different services in separate terminal windows:

*   **FastAPI Web App (Webhook Router & Auth API)**:
    ```bash
    uvicorn src.main:app --reload --port 8000
    ```
*   **Celery Worker (Mail processing & attachment scanning)**:
    ```bash
    celery -A src.tasks.worker.celery_app worker --loglevel=info
    ```
*   **Celery Beat Scheduler (Reminders & Watch Renewals)**:
    ```bash
    celery -A src.tasks.worker.celery_app beat --loglevel=info
    ```

---

## 🧪 Testing

The project uses `pytest` with `pytest-asyncio` and in-memory SQLite database setups for fast local validation.

Run the entire test suite:
```bash
python -m pytest
```

---

## 📁 Project Structure

```text
PlacementBot/
├── .planning/            # Project Roadmap, Milestones, and Architectural Context
├── src/
│   ├── api/              # API Routes (Auth, Webhook, Health, Prometheus)
│   ├── core/             # AI Gateway, Attachment Parsers, Encryption, Logger, Metrics
│   ├── models/           # SQLAlchemy DB Models (User, Reminder, DLQ, AuditLog)
│   ├── tasks/            # Celery Asynchronous Tasks & Beat scheduler setup
│   └── main.py           # Application Entry point
├── tests/                # Unit and Integration test suite
├── Dockerfile            # Packaging config
├── docker-compose.yml    # Service definitions for local environment
└── requirements.txt      # Python dependencies
```
