# Domain Pitfalls

**Domain:** Secure Email Notification & AI-Parsing Systems
**Researched:** 2026-06-08

## Critical Pitfalls

### Pitfall 1: Silent Expiration of Gmail Watch Subscriptions
- **What goes wrong:** A student ceases to receive placement alerts because the Gmail watch subscription silently expires.
- **Why it happens:** The Google Gmail API `watch()` subscription has a maximum TTL of 7 days. Once expired, Google stops publishing mailbox updates to the Pub/Sub topic.
- **Consequences:** Missed placement deadlines, causing direct user impact.
- **Prevention:** Implement a Celery Beat task that runs daily and registers a fresh `watch()` for all active users in the database, resetting the 7-day expiration window.
- **Detection:** Log watch expiration timestamps in PostgreSQL. Create an audit check that alerts the admin if any user's watch is less than 48 hours from expiration.

### Pitfall 2: Webhook Retries and Event Storms
- **What goes wrong:** FastAPI webhook becomes unresponsive, creating a backlog of hundreds of duplicate events in GCP Pub/Sub.
- **Why it happens:** If the webhook takes too long to process an email (e.g., waiting for Gemini API or attachment downloads), the connection times out. Pub/Sub assumes delivery failed and retries.
- **Consequences:** High CPU usage, rate limit exhaustion, and duplicate Telegram messages.
- **Prevention:** Fast-ACK. Validate the request header and push the payload immediately into Celery. Return HTTP 200 `{"status": "queued"}` in less than 50 milliseconds.
- **Detection:** Log the latency of the webhook endpoint. Track `x-pubsub-delivery-attempt` headers.

### Pitfall 3: OAuth Token Revocation or Expiry
- **What goes wrong:** Background workers raise authentication errors when attempting to query the Gmail API.
- **Why it happens:** Users can revoke access to the Google OAuth app from their Google account dashboard, or Google can expire refresh tokens (e.g., if the GCP OAuth screen is set to "Testing" and the token is unused for 7-14 days).
- **Consequences:** Background worker fails. User notifications break.
- **Prevention:** Wrap all Gmail API interactions in try-except blocks catching OAuth exceptions. If a token is invalid, disable the watch, flag the user's account status in the DB, and send an urgent Telegram alert asking them to re-authenticate.
- **Detection:** Monitor workers for `google.auth.exceptions.RefreshError`.

## Moderate Pitfalls

### Pitfall 1: Large Spreadsheet Memory / Token Limits
- **What goes wrong:** Worker crashes when parsing massive Excel lists of placement shortlists.
- **Why it happens:** Shortlist Excel files can contain thousands of rows. Parsing them into raw text and feeding them to Gemini uses excessive tokens and can hit API limit boundaries.
- **Prevention:** Perform pre-filtering of sheets. Use `openpyxl` in python to extract all strings, check for the user's specific registration number pattern locally first. Only send relevant chunks to Gemini for contextual verification.

### Pitfall 2: OIDC Signature Out-of-Sync Certificate Caches
- **What goes wrong:** The webhook endpoint starts rejecting valid Google Pub/Sub pushes with signature errors.
- **Why it happens:** Google rotates public certificates used to sign OIDC JWTs. If the validator caches public keys statically, validation will fail post-rotation.
- **Prevention:** Use the `google-auth` library's verify token method, which automatically manages caching and fetches updated public keys from `https://www.googleapis.com/oauth2/v3/certs`.

## Minor Pitfalls

### Pitfall 1: OCR Mismatches on Student Identifiers
- **What goes wrong:** A student is shortlisted, but they do not get notified because OCR parses "23BIT0117" as "23BlT0ll7" (substituting letters for numbers).
- **Prevention:** Match using fuzzy logic on names and strip spaces/punctuation from registration numbers. Ask Gemini to identify names and register numbers and normalize them inside its JSON response.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Ingestion & Webhooks | Webhook Timeout | Implement Celery broker immediately; do not perform API work inline. |
| Ingestion & Webhooks | Duplicate Messages | Enable Redis-based idempotency locks on `message_id` with 24h expiration. |
| Attachment Parsing | Gemini Cost Spike | Apply deterministic local regex checks for student ID before invoking Gemini API. |
| Security | Leak of OAuth Credentials | Keep DB columns encrypted with Fernet (AES-256) and store keys only in Railway Env. |

## Sources
- Google OAuth token expiration policies: https://developers.google.com/identity/protocols/oauth2#expiration
- Google Pub/Sub retry backoff: https://cloud.google.com/pubsub/docs/subscriber-retry-settings
