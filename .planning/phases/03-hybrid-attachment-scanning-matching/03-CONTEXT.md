# Phase 3: Hybrid Attachment Scanning & Matching - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the capability to download and process email attachments (PDFs, Excel sheets, and images) to check if the student is shortlisted or matched in them. It implements a hybrid parsing architecture: running deterministic local text extraction first, falling back to local OCR, and escalates to the Gemini Vision API only under confidence-based failure conditions.

</domain>

<decisions>
## Implementation Decisions

### Local OCR Engine
- **D-20:** We will use `pytesseract` locally for CPU-efficient, fast extraction of text from images. This will require installing the `tesseract-ocr` system package in our Docker container during the deployment phase.

### Storage Management (Privacy-First)
- **D-21:** Downloaded attachments must be processed **100% in-memory** using `io.BytesIO` or PIL Images. Attachment binaries must never be written to the local disk, adhering strictly to our data minimization and privacy guidelines.

### Parsing Scope
- **D-22:** **Excel Files:** Scan all sheets in multi-sheet Excel files to prevent missing shortlist divisions (such as sheets split by department).
- **D-23:** **PDF Files:** Limit deterministic text extraction using `pdfplumber` to the first 10 pages of any PDF document to prevent excessive memory/CPU load on large files.

### Gemini Vision Escalation Policy
- **D-24:** Trigger Gemini Vision only under the following confidence-based escalation conditions:
  1. The PDF is scanned/image-only (meaning text extraction returns near-zero characters of text).
  2. Local Tesseract OCR confidence score on image attachments is below 80%.
  3. The attachment appears to contain a structured table, but the local text extraction result is poor/scrambled.
  4. Local parsing libraries throw exceptions/errors.
- **D-25:** Do **NOT** trigger Gemini Vision merely because a student identifier was not found in a cleanly parsed text document.

### Developer Discretion
- The exact prompt wording for Gemini Vision table extraction and the choice of specific confidence threshold structures (beyond the 80% OCR baseline) are left to developer/agent discretion.

</decisions>

<canonical_refs>
## Canonical References

### Project Scope & Guidelines
- [ROADMAP.md](file:///.planning/ROADMAP.md) — Contains the goals and success criteria for Phase 3.
- [GEMINI.md](file:///GEMINI.md) — Standardizes architectural constraints (hybrid structure, data minimization, least privilege).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- [CredentialEncryptor](file:///src/core/security.py): Reused to decrypt the student's register number, NeoPAT ID, and email addresses.
- [check_student_identifiers](file:///src/core/pre_check.py): Reused to match student identifiers within extracted text.
- [AIGateway](file:///src/core/ai_gateway.py): Can be updated or extended to handle Gemini Vision multimodal calls using `google-genai`'s `.aio` interface.
- [send_telegram_alert](file:///src/core/telegram_dispatcher.py): Reused to dispatch notifications.

### Integration Points
- **Worker Pipeline:** Integration will hook into `process_email_pipeline_async` in [email_tasks.py](file:///src/tasks/email_tasks.py). After downloading the email body, we will fetch any attachments listed in the Gmail message metadata, parse them using our hybrid logic, and run matches on them.

</code_context>

<specifics>
## Specific Ideas
- No specific layout examples. We will prioritize extracting plain text lines and running regex/substring matches against the student's identifiers.

</specifics>

<deferred>
## Deferred Ideas
- None — all discussed items stayed within the scope of Phase 3.

</deferred>

---

*Phase: 3-Hybrid Attachment Scanning & Matching*
*Context gathered: 2026-06-10*
