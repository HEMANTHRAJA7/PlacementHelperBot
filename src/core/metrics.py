from prometheus_client import Counter, Gauge

# active_watches_total (Gauge: healthy vs expired)
ACTIVE_WATCHES = Gauge(
    "active_watches_total",
    "Number of active watches by status",
    ["status"]
)

# ai_cost_usd_total (Counter)
AI_COST_USD = Counter(
    "ai_cost_usd_total",
    "Total AI cost in USD"
)

# ai_tokens_total (Counter: prompt and generation tokens, labeled by model)
AI_TOKENS = Counter(
    "ai_tokens_total",
    "Total AI tokens processed",
    ["model", "type"]
)

# notifications_sent_total (Counter: notifications sent, labeled by category)
NOTIFICATIONS_SENT = Counter(
    "notifications_sent_total",
    "Total notifications sent",
    ["category"]
)

# dlq_failures_total (Counter)
DLQ_FAILURES = Counter(
    "dlq_failures_total",
    "Total failed jobs routed to DLQ"
)

# gmail_events_processed_total (Counter)
GMAIL_EVENTS_PROCESSED = Counter(
    "gmail_events_processed_total",
    "Total incoming unique push events processed"
)

# gmail_duplicate_events_total (Counter)
GMAIL_DUPLICATE_EVENTS = Counter(
    "gmail_duplicate_events_total",
    "Total incoming duplicate push events dropped"
)

# ai_failures_total (Counter)
AI_FAILURES = Counter(
    "ai_failures_total",
    "Total failed AI Gateway requests"
)

# telegram_delivery_failures_total (Counter)
TELEGRAM_DELIVERY_FAILURES = Counter(
    "telegram_delivery_failures_total",
    "Total failed Telegram API calls"
)

# attachment_parse_failures_total (Counter)
ATTACHMENT_PARSE_FAILURES = Counter(
    "attachment_parse_failures_total",
    "Total failed PDF/Excel/OCR extractions"
)

# attachment_matches_total (Counter)
ATTACHMENT_MATCHES = Counter(
    "attachment_matches_total",
    "Total matches found in attachments"
)

# celery_pending_tasks_total (Gauge: pending/active tasks in queue)
CELERY_PENDING_TASKS = Gauge(
    "celery_pending_tasks_total",
    "Total pending/active Celery tasks"
)

# gmail_watch_renew_failures_total (Counter)
GMAIL_WATCH_RENEW_FAILURES = Counter(
    "gmail_watch_renew_failures_total",
    "Total failed daily watch renewals"
)
