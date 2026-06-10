---
phase: 04-lifecycle-privacy-observability
plan: 01
subsystem: api
tags: [celery, postgres, google-api]

requires: []
provides:
  - Gmail watch renewal background tasks
  - User model tracking active watches and expiration
affects: [monitoring]

tech-stack:
  added: []
  patterns: [Celery periodic task, Celery task retries with backoff]

key-files:
  created: [tests/test_lifecycle.py]
  modified: [src/models/user.py, src/core/gmail.py, src/tasks/worker.py, src/tasks/email_tasks.py]

key-decisions:
  - "Watch renewal retries 3 times with exponential backoff before sending a warning and setting watch_active=False."

patterns-established:
  - "Retry logic inside task for Gmail Watch renewals"

requirements-completed: [INGST-07, INGST-08]

duration: 15min
completed: 2026-06-10
---

# Phase 4: Lifecycle, Privacy, & Observability - Plan 01 Summary

**Gmail Watch renewal background tasks and DB columns implemented**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-10T13:00:00Z
- **Completed:** 2026-06-10T13:15:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- User model columns added to store watch_active, watch_resource_id, watch_expiration.
- setup_gmail_watch added to fetch watch subscription.
- Celery task renew_single_user_watch_task implemented with 3 retries (backoff) and warning dispatch.

## Files Created/Modified
- `src/models/user.py` - Added watch tracking fields to User
- `src/core/gmail.py` - Implemented setup_gmail_watch POST request
- `src/tasks/worker.py` - Registered watch renewal in Celery Beat
- `src/tasks/email_tasks.py` - Implemented renew_all_watches_task and renew_single_user_watch_task
- `tests/test_lifecycle.py` - Created tests for watch renewals

## Decisions Made
- None - followed plan as specified.

## Deviations from Plan
- None - plan executed exactly as written.
