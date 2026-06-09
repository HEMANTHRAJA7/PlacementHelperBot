# Phase 2: Core Processing, AI Gateway, & Telegram Bot - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 02-core-processing-ai-gateway-telegram-bot
**Areas discussed:** AI Gateway Model & Cost Tracking, Telegram Notification Styling & Priority, Deterministic Local Pre-Check rules, AI Gateway Rate Limiting & Retry Backoffs

---

## AI Gateway Model & Cost Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| gemini-2.0-flash | Fast, cost-efficient, and natively supports Pydantic structured outputs | ✓ |
| gemini-2.0-pro | Higher capability for reasoning, but increased latency and cost | |

**User's choice:** gemini-2.0-flash

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL database tables | Store raw token counts and computed USD cost in a dedicated audit/usage log table | ✓ |
| Redis cache with daily rollups | Lighter but ephemeral, loses detailed history after TTL | |
| STDOUT logs only | Simplest, zero database overhead, but no persistent auditing capability | |

**User's choice:** PostgreSQL database tables

**Notes:** 
- A hybrid fallback strategy was decided:
  1. Retry the primary Gemini model 3 times using exponential backoff (5s, 30s, 120s).
  2. If Gemini remains unavailable, fall back to deterministic rule-based classification (extract subject, sender, deadlines, and identifiers using local parsers).
  3. If classification confidence is insufficient, send a generic placement notification: *"Placement-related email detected. Please check your VIT mail."*
  4. Log AI failure metrics and move detailed failure information to audit logs.
  5. Only route the event to the Celery DLQ if both the AI and deterministic processing fail.

---

## Telegram Notification Styling & Priority

| Option | Description | Selected |
|--------|-------------|----------|
| HTML format | Much safer than MarkdownV2 since arbitrary company names, packages, and URLs do not require strict character escaping, preventing Telegram parser crashes | ✓ |
| MarkdownV2 format | Sleeker monospaced layout, but requires escaping special characters like '.', '-', '!', '(', ')') | |

**User's choice:** HTML format

| Option | Description | Selected |
|--------|-------------|----------|
| Custom emoji badges per priority | Emoji badges (🔴 Offer, 🟡 Shortlist, 🔵 Interview, 🟢 Assessment, ⚪ Opportunity) with bold headers and metadata tables | ✓ |
| Simple flat text layout | Simple flat text layout with priority name inside brackets | |

**User's choice:** Custom emoji badges per priority

**Notes:**
- Telegram notifications will *always* be delivered silently (`disable_notification=True` in the API call) to prevent student distraction.

---

## Deterministic Local Pre-Check rules

| Option | Description | Selected |
|--------|-------------|----------|
| Exact case-insensitive substring search | Safe and fast for Register Numbers, NeoPAT IDs, and Email addresses; split name into tokens and require at least two name tokens to match | ✓ |
| Strict exact match | Matches the complete name and ID strings exactly | |

**User's choice:** Exact case-insensitive substring search

| Option | Description | Selected |
|--------|-------------|----------|
| Proceed to Gemini AI classification | The email might be a batch-wide opportunity or the student might be shortlisted in an attachment scanned in Phase 3 | ✓ |
| Filter out the email immediately as a non-match | Do not call Gemini AI or send notifications | |

**User's choice:** Proceed to Gemini AI classification

**Notes:** None.

---

## AI Gateway Rate Limiting & Retry Backoffs

| Option | Description | Selected |
|--------|-------------|----------|
| Redis-based token bucket rate limiter | Exposes a global limit in Redis to prevent multiple Celery tasks from concurrently hitting Gemini 429 rate limits | ✓ |
| Celery-level task rate limit | Task decorator rate limit e.g. rate_limit='10/m' | |
| Passive retry only | Catch HTTP 429 exceptions and rely solely on Celery task retries with backoff | |

**User's choice:** Redis-based token bucket rate limiter

| Option | Description | Selected |
|--------|-------------|----------|
| YAML files in the codebase | Store prompt templates in a src/core/prompts/ folder, versioned by filename or keys, and log the active version in usage tables | ✓ |
| Database-stored prompts | Store prompts in a prompts table | |

**User's choice:** YAML files in the codebase

| Option | Description | Selected |
|--------|-------------|----------|
| Comprehensive cost audit log | Fields include: id (PK), model_name (str), prompt_version (str), input_tokens (int), output_tokens (int), estimated_cost_usd (numeric), message_id (str), status (str), created_at (timestamp) | ✓ |
| Basic summary log | Store only model name and total estimated cost per user profile | |

**User's choice:** Comprehensive cost audit log

**Notes:** None.

---

## the agent's Discretion

- Redis rate-limiter bucket size limits and exact key namespace formatting.
- Precise layout details of the Telegram HTML message structure.
- Details of the local rule-based parsing engine fallback parser logic.

---

## Deferred Ideas

- Model fallback to `gemini-1.5-flash` — deferred in favor of rule-based deterministic parsing.
- Interactive bot features (status checks, registration updates, pause/mute commands) — deferred to CHAT-01/CHAT-02 (v2 requirements).
