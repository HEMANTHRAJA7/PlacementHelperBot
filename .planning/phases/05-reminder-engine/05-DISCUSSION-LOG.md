# Discussion Log: Phase 5 - Reminder Engine

This log documents the alignment and decisions reached for the Reminder Engine.

## Questions & Answers

### 1. Database Table Schema
*   **Question**: Does the proposed reminders schema look correct, or are there additional fields you would like to track?
*   **Decision**: Adopted the recommended schema, including additional fields for tracking:
    *   `last_reminder_sent_at` (DateTime)
    *   `status` (`"ACTIVE"`, `"EXPIRED"`, or `"COMPLETED"`)
    *   `source_email_id` (representing the Gmail message ID)
    *   `updated_at` (for tracking modifications)

### 2. Notification Priority & sound
*   **Question**: Should urgent reminders (1h/6h) play sound or bypass silent modes?
*   **Decision**: Bypassed sound management in code. All Placement Sentinel alerts will be sent using normal delivery (`disable_notification=False`), allowing students to manage their sound and mute behaviors through Telegram and OS-level settings.

### 3. Check Frequency & Catch-Up Behavior
*   **Question**: How frequently should Celery Beat run, and should we handle missed reminders (catch-up)?
*   **Decision**:
    *   **Check Frequency**: Run the Celery Beat task every 5 minutes.
    *   **Catch-Up Policy**: Option A (Catch-up) is selected with a Max catch-up age of 2 hours. If a task was offline, it will catch up on any alert that was missed within the last 2 hours.

### 4. Category Filtering
*   **Question**: Which categories of notifications should schedule recurring reminders?
*   **Decision**:
    *   **Reminders Scheduled**: `"Opportunity"`, `"Assessment"`, and `"Interview"`.
    *   **Reminders Excluded**: `"Shortlist"`, `"Offer"`, and `"Rejection"`.
