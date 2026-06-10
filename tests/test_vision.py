import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from src.core.ai_gateway import AIGateway, AttachmentMatchingResult
from src.models.user import AIUsageLog
from sqlalchemy import select

@pytest.mark.asyncio
@patch("src.core.ai_gateway.AIGateway.check_rate_limit", return_value=True)
async def test_ai_gateway_classify_attachment_vision_success(mock_rate_limit, db_session):
    """Verify that classify_attachment_vision successfully sends multimodal content to Gemini and records usage."""
    gateway = AIGateway(api_key="mock_key")
    
    mock_response = MagicMock()
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = 500
    mock_response.usage_metadata.candidates_token_count = 150
    
    mock_result = AttachmentMatchingResult(
        is_matched=True,
        matched_identifier="21BCE0001",
        confidence=0.95,
        reason="Found on row 5 under Register Number column."
    )
    mock_response.parsed = mock_result
    
    gateway.client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    
    student_info = {
        "full_name": "Hemanth Raja S",
        "register_number": "21BCE0001",
        "neopat_id": "NP001",
        "email": "student@vitstudent.ac.in"
    }
    
    res = await gateway.classify_attachment_vision(
        attachment_bytes=b"fake_image_bytes",
        mime_type="image/png",
        student_info=student_info,
        message_id="msg_999"
    )
    
    assert res.is_matched is True
    assert res.matched_identifier == "21BCE0001"
    assert res.confidence == 0.95
    assert "row 5" in res.reason
    
    # Verify usage was logged to db
    result = await db_session.execute(select(AIUsageLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].input_tokens == 500
    assert logs[0].output_tokens == 150
