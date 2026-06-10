# Phase 5: Reminder Engine - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers scheduled reminders for upcoming placement events and application deadlines:
1. Daily or periodic Celery Beat task running every 5 minutes to scan upcoming deadlines and dispatch notifications.
2. Reminder tracking database table mapping user, company, role, event category, deadline timestamp, reminder status, and catch-up options.
3. Priority-based reminder alerts delivered with normal notifications (`disable_notification=False`) according to VIT student requirements.

</domain>

<decisions>
## Implementation Decisions

### Reminder Database Schema
- **D-37:** A new database table `reminders` will store deadline-related event details:
  - `id` (PK, Integer)
  - `user_id` (FK to users)
  - `company` (String, nullable)
  - `role` (String, nullable)
  - `category` (String)
  - `deadline_at` (DateTime, timezone-aware)
  - `reminded_24h` (Boolean, default=False)
  - `reminded_6h` (Boolean, default=False)
  - `reminded_1h` (Boolean, default=False)
  - `last_reminder_sent_at` (DateTime, nullable)
  - `status` (String: `"ACTIVE"`, `"EXPIRED"`, or `"COMPLETED"`)
  - `source_email_id` (String referencing Gmail message ID, nullable)
  - `created_at` (DateTime, default=func.now())
  - `updated_at` (DateTime, default=func.now(), onupdate=func.now())

### Notification Delivery Policy
- **D-38:** All Telegram notifications (including reminders and priority alerts) will be sent with normal delivery status (`disable_notification=False`).
- **D-39:** The system does not attempt to manage sound, mute, or vibration settings; users configure this via Telegram application settings and device priority options.

### Scheduler Frequency & Catch-Up Behavior
- **D-40:** A Celery Beat scheduler task will run every 5 minutes to scan active reminders.
- **D-41:** **Catch-Up Policy**: If a reminder window was missed (e.g. system downtime), the scheduler will catch up and dispatch the alert immediately upon recovery, provided:
  - The deadline has not passed yet.
  - The difference between the scheduled reminder time (e.g., deadline - 6h) and current time is less than **2 hours** (Max Catch-Up Age). If the gap is wider than 2 hours, the missed alert window is skipped.

### Eligible Categories
- **D-42:** Scheduled reminders will be created and triggered only for:
  - `"Opportunity"` (e.g. registrations/deadlines)
  - `"Assessment"` (e.g. test links/times)
  - `"Interview"` (e.g. scheduled slots)
- **D-43:** No recurring reminders will be scheduled for:
  - `"Shortlist"`
  - `"Offer"`
  - `"Rejection"`

</decisions>

<canonical_refs>
## Canonical References
- [ROADMAP.md](file:///.planning/ROADMAP.md) — Phase 5 definition and success metrics.
- [REQUIREMENTS.md](file:///.planning/REQUIREMENTS.md) — Requirement REM-01 mapping.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- [email_tasks.py](file:///src/tasks/email_tasks.py): Houses the primary celery worker async event loops and model retrievals.
- [telegram_dispatcher.py](file:///src/core/telegram_dispatcher.py): Implements `send_telegram_alert`. We must modify `disable_notification=False` here.

### Integration Points
- When the AI Gateway classifies an email as `PlacementCategory.OPPORTUNITY`, `PlacementCategory.ASSESSMENT`, or `PlacementCategory.INTERVIEW`, and parses a valid `deadline` date:
  - Parse the date string into a timezone-aware datetime.
  - Insert a new `Reminder` record in the database with status `"ACTIVE"`.
  - In `renew_single_user_watch_task`, if a user's watch renewal fails and they are marked inactive, we may transition related active reminders to `"EXPIRED"` or keep them active depending on re-authentication.

</code_context>

<deferred>
## Deferred Ideas
- None.

</deferred>

---

*Phase: 5-Reminder-Engine*
*Context gathered: 2026-06-10*
