# Phase 2: Core Processing, AI Gateway, & Telegram Bot - Research

**Researched:** 2026-06-09
**Domain:** Background email parsing, Pydantic Gemini structured output, Redis rate-limiting, and silent Telegram bot dispatch.
**Confidence:** HIGH

---

## User Constraints

Downstream agents MUST honor these constraints. Copied from [02-CONTEXT.md](file:///.planning/phases/02-core-processing-ai-gateway-telegram-bot/02-CONTEXT.md):
- **D-09:** Use `gemini-2.0-flash` as the primary engine for classification and metadata extraction.
- **D-10:** Persist token usage and computed USD costs in a dedicated PostgreSQL database table (`ai_usage_logs`).
- **D-11:** If the primary Gemini model fails, retry 3 times with exponential backoff. If unavailable, fall back to local deterministic rule-based parsing. If classification confidence is insufficient, send a generic placement alert: *"Placement-related email detected. Please check your VIT mail."* Log failures, and only route to DLQ if both AI and deterministic processing fail.
- **D-12:** Telegram notifications must be formatted in HTML (safer and cleaner parsing than MarkdownV2, preventing crash loops on special characters in company names).
- **D-13:** Alerts must be visually styled with bold headers, custom priority emoji badges (🔴 Offer, 🟡 Shortlist, 🔵 Interview, 🟢 Assessment, ⚪ Opportunity), and metadata tables.
- **D-14:** Telegram notifications must *always* be delivered silently (`disable_notification=True` in the API call) to prevent student distraction.
- **D-15:** Run exact case-insensitive substring search in the email body for Register Numbers, NeoPAT IDs, and Emails. For Names, split the name into tokens and require at least two name tokens to match.
- **D-16:** If no student identifiers are matched in the body by the pre-check, still proceed to Gemini AI classification (could be a batch-wide opportunity or attachment shortlist).
- **D-17:** Implement a Redis-based token bucket rate limiter to prevent multiple Celery tasks from concurrently hitting Gemini 429 rate limits, delaying execution of tasks when quotas are exceeded.
- **D-18:** Store prompt templates in YAML files inside the codebase (under `src/core/prompts/`), versioned by filename/keys, and log the active version in usage tables.
- **D-19:** The `ai_usage_logs` database schema must include: `id` (PK), `model_name` (str), `prompt_version` (str), `input_tokens` (int), `output_tokens` (int), `estimated_cost_usd` (numeric), `message_id` (str), `status` (str), and `created_at` (timestamp).

---

## Summary

This phase implements the heart of the notification pipeline. Background Celery workers retrieve email payloads from the Gmail API using decrypted OAuth refresh tokens. 

The pipeline runs a local deterministic pre-check on the email body looking for candidate identifiers. If identifiers are missing, it still forwards the text to the AI Gateway to check for batch-wide opportunities or prepare for attachment-level lists.

The **AI Gateway** centralizes all Gemini API interactions. It loads prompt templates from versioned YAML files and executes calls using the new `google-genai` Python library, enforcing Pydantic models in the `response_schema` to guarantee structured JSON outputs. Token usage is logged, costs are estimated (e.g., input: $0.075 / 1M, output: $0.30 / 1M for Gemini 2.0 Flash), and saved to a PostgreSQL `ai_usage_logs` table. A Redis Lua script enforces a token-bucket rate limiter to prevent API 429s.

Finally, verified placement events are prioritized and pushed as silent HTML-formatted alerts to the student's Telegram account.

---

## Technical Integration Details

### 1. Gmail API Mail Retrieval
Using the `google-auth` credential helper and `googleapiclient.discovery` (installed via google-api-python-client, or direct HTTPS request via `httpx` to minimize heavy dependencies).
We can make direct HTTPS requests to `https://gmail.googleapis.com/gmail/v1/users/me/messages/{id}?format=full` using `httpx` with the user's access token, which is lightweight, asynchronous, and fast.
Example structure of message parsing:
```python
async def fetch_gmail_message(access_token: str, message_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"}
        )
        response.raise_for_status()
        return response.json()
```

### 2. Google GenAI SDK (google-genai) Structured Output
```python
from google import genai
from pydantic import BaseModel, Field
from typing import Optional

class EmailClassification(BaseModel):
    is_placement_related: bool = Field(description="True if the email contains placement, internship, shortlist, or assessment content.")
    classification: str = Field(description="One of: PLACEMENT_OPPORTUNITY, INTERNSHIP, ASSESSMENT, SHORTLIST, INTERVIEW, OFFER, REJECTION, OTHER")
    company_name: Optional[str] = Field(description="Name of the recruiting company.")
    role: Optional[str] = Field(description="Job profile or role name.")
    package: Optional[str] = Field(description="Salary package or stipend details if mentioned.")
    deadline: Optional[str] = Field(description="Application deadline or event date.")
    application_link: Optional[str] = Field(description="URL link to apply or register if found in the email body.")

def analyze_email_with_ai(email_body: str, prompt_template: str) -> EmailClassification:
    client = genai.Client()
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"{prompt_template}\n\nEmail Content:\n{email_body}",
        config={
            'response_mime_type': 'application/json',
            'response_schema': EmailClassification,
        }
    )
    # response.parsed contains the parsed Pydantic model
    return response.parsed, response.usage_metadata
```

### 3. Redis Lua token-bucket rate limiter
```python
RATE_LIMIT_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + (elapsed * refill_rate))

local allowed = 0
if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
redis.call('EXPIRE', key, 60)

return allowed
"""
```

### 4. HTML Message Formatter
HTML styling for the Telegram Bot API `sendMessage`:
```python
def format_telegram_alert(classification: str, company: str, role: str, package: str, deadline: str, link: str) -> str:
    badges = {
        "OFFER": "🔴 <b>OFFER DETECTED</b>",
        "SHORTLIST": "🟡 <b>SHORTLIST UPDATE</b>",
        "INTERVIEW": "🔵 <b>INTERVIEW SCHEDULED</b>",
        "ASSESSMENT": "🟢 <b>ASSESSMENT ANNOUNCEMENT</b>",
        "PLACEMENT_OPPORTUNITY": "⚪ <b>PLACEMENT OPPORTUNITY</b>",
        "INTERNSHIP": "⚪ <b>INTERNSHIP OPPORTUNITY</b>",
        "REJECTION": "⚪ <b>PLACEMENT STATUS</b>"
    }
    
    header = badges.get(classification, "⚪ <b>PLACEMENT Sentinel NOTIFICATION</b>")
    
    html = f"{header}\n\n"
    html += f"<b>Company:</b> {company or 'N/A'}\n"
    if role:
        html += f"<b>Role:</b> {role}\n"
    if package:
        html += f"<b>Package:</b> {package}\n"
    if deadline:
        html += f"<b>Deadline/Date:</b> {deadline}\n"
    if link:
        html += f"\n<a href='{link}'><b>👉 Apply / View Link</b></a>\n"
        
    return html
```

---

## Validation Strategy (Nyquist)

### Test Command Mapping
- Unit tests: `python -m pytest tests/test_processing.py`
- Integration tests: `python -m pytest tests/test_gateway.py`
- Telegram Dispatcher checks: `python -m pytest tests/test_bot.py`

### Per-Task Verification Map
- **Task 2.1:** Retrieve mail & pre-check: verify case-insensitive matching & token name split matches (`tests/test_processing.py`).
- **Task 2.2:** AI Gateway: verify model output schemas, rate limiting retries, and cost persistence (`tests/test_gateway.py`).
- **Task 2.3:** Telegram Bot: verify HTML construction, priorities, and silent dispatch (`tests/test_bot.py`).
