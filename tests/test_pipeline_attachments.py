import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.tasks.email_tasks import process_email_event
from src.models.user import User
from src.core.security import CredentialEncryptor
from src.core.ai_gateway import ClassificationResult, PlacementCategory, AttachmentMatchingResult

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.fetch_gmail_attachment", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_pdf_in_memory")
@patch("src.tasks.email_tasks.AIGateway.classify_email", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_pdf_deterministic_match(
    mock_send_tg, mock_classify_email, mock_parse_pdf, mock_fetch_attachment,
    mock_parse_msg, mock_fetch_msg, mock_refresh, db_session
):
    """Verify that a PDF attachment with student ID is parsed deterministically and triggers matched notification."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=1234567,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("refresh_tok"),
        encrypted_register_number=encryptor.encrypt("21BCE0001")
    )
    db_session.add(user)
    await db_session.commit()
    
    mock_refresh.return_value = "access_tok"
    mock_fetch_msg.return_value = {
        "id": "msg_pdf_1",
        "payload": {
            "parts": [
                {
                    "filename": "shortlist.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att_pdf_123"}
                }
            ]
        }
    }
    mock_parse_msg.return_value = ("Microsoft Drive", "VIT Office", "General body info.")
    mock_fetch_attachment.return_value = b"pdf_binary_content"
    mock_parse_pdf.return_value = "Row 4: 21BCE0001 Selected SDE"
    
    mock_classify_email.return_value = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.SHORTLIST,
        company="Microsoft",
        role="SDE",
        package="45 LPA",
        deadline="June 18",
        application_links=[],
        confidence=0.99
    )
    
    process_email_event(email="student@vitstudent.ac.in", history_id=2001, message_id="msg_pdf_1")
    
    mock_send_tg.assert_called_once()
    tg_id, text = mock_send_tg.call_args[0]
    assert tg_id == 1234567
    assert "Matched in attachment: shortlist.pdf" in text
    assert "Microsoft" in text

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.fetch_gmail_attachment", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_pdf_in_memory")
@patch("src.tasks.email_tasks.AIGateway.classify_email", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.AIGateway.classify_attachment_vision", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_scanned_pdf_escalation(
    mock_send_tg, mock_classify_vision, mock_classify_email, mock_parse_pdf,
    mock_fetch_attachment, mock_parse_msg, mock_fetch_msg, mock_refresh, db_session
):
    """Verify scanned PDFs (empty text) trigger Gemini Vision escalation matching."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=1234567,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("refresh_tok"),
        encrypted_register_number=encryptor.encrypt("21BCE0001")
    )
    db_session.add(user)
    await db_session.commit()
    
    mock_refresh.return_value = "access_tok"
    mock_fetch_msg.return_value = {
        "id": "msg_scanned_1",
        "payload": {
            "parts": [
                {
                    "filename": "scanned.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att_scanned_123"}
                }
            ]
        }
    }
    mock_parse_msg.return_value = ("Shortlist Out", "VIT Office", "Check PDF.")
    mock_fetch_attachment.return_value = b"scanned_pdf_binary_content"
    mock_parse_pdf.return_value = "   "
    
    mock_classify_email.return_value = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.SHORTLIST,
        company="Microsoft",
        role="SDE",
        package=None,
        deadline=None,
        application_links=[],
        confidence=0.99
    )
    
    mock_classify_vision.return_value = AttachmentMatchingResult(
        is_matched=True,
        matched_identifier="21BCE0001",
        confidence=0.98,
        reason="Found SDE candidate 21BCE0001 on the image page."
    )
    
    process_email_event(email="student@vitstudent.ac.in", history_id=2002, message_id="msg_scanned_1")
    
    mock_classify_vision.assert_called_once()
    mock_send_tg.assert_called_once()
    assert "Matched in attachment: scanned.pdf" in mock_send_tg.call_args[0][1]

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.fetch_gmail_attachment", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_image_in_memory")
@patch("src.tasks.email_tasks.AIGateway.classify_email", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.AIGateway.classify_attachment_vision", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_low_confidence_ocr_escalation(
    mock_send_tg, mock_classify_vision, mock_classify_email, mock_parse_image,
    mock_fetch_attachment, mock_parse_msg, mock_fetch_msg, mock_refresh, db_session
):
    """Verify that images with low Tesseract confidence trigger Gemini Vision escalation."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=1234567,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("refresh_tok"),
        encrypted_register_number=encryptor.encrypt("21BCE0001")
    )
    db_session.add(user)
    await db_session.commit()
    
    mock_refresh.return_value = "access_tok"
    mock_fetch_msg.return_value = {
        "id": "msg_image_1",
        "payload": {
            "parts": [
                {
                    "filename": "screenshot.png",
                    "mimeType": "image/png",
                    "body": {"attachmentId": "att_image_123"}
                }
            ]
        }
    }
    mock_parse_msg.return_value = ("SDE List", "VIT Office", "Screenshot attached.")
    mock_fetch_attachment.return_value = b"image_binary_content"
    mock_parse_image.return_value = ("Garbled Text 21BCE0001", 65.0)
    
    mock_classify_email.return_value = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.SHORTLIST,
        company="Microsoft",
        role="SDE",
        package=None,
        deadline=None,
        application_links=[],
        confidence=0.99
    )
    
    mock_classify_vision.return_value = AttachmentMatchingResult(
        is_matched=True,
        matched_identifier="21BCE0001",
        confidence=0.99,
        reason="Found on WhatsApp screenshot."
    )
    
    process_email_event(email="student@vitstudent.ac.in", history_id=2003, message_id="msg_image_1")
    
    mock_classify_vision.assert_called_once()
    mock_send_tg.assert_called_once()
