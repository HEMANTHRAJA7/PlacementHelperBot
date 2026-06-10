import pytest
from unittest.mock import MagicMock, patch
from src.core.gmail import fetch_gmail_message, parse_gmail_message
from src.core.pre_check import check_student_identifiers

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_gmail_message_fetch(mock_get):
    """Verify fetch_gmail_message downloads and decodes headers and payload parts successfully."""
    mock_payload = {
        "id": "msg_12345",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Placement Shortlist for Microsoft"},
                {"name": "From", "value": "VIT Placement Office <placement@vit.ac.in>"}
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "size": 50,
                        # Base64url encoded: "Hello student, you are shortlisted for Microsoft."
                        "data": "SGVsbG8gc3R1ZGVudCwgeW91IGFyZSBzaG9ydGxpc3RlZCBmb3IgTWljcm9zb2Z0Lg=="
                    }
                }
            ]
        }
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_get.return_value = mock_response
    
    # Verify raw HTTP retrieval
    data = await fetch_gmail_message("mock_access_token", "msg_12345")
    assert data["id"] == "msg_12345"
    
    # Verify parser extracts fields accurately
    subject, sender, body = parse_gmail_message(data)
    assert subject == "Placement Shortlist for Microsoft"
    assert sender == "VIT Placement Office <placement@vit.ac.in>"
    assert "shortlisted for Microsoft" in body

def test_pre_check_matching():
    """Verify deterministic matching rules on student identifiers."""
    body = "Dear Hemanth Raja S, your VIT register number 21BCE0001 is shortlisted. Contact neopat ID NP0099. Mail at student@vitstudent.ac.in"
    
    # 1. Register Number match
    assert check_student_identifiers(body, register_number="21bce0001") is True
    assert check_student_identifiers(body, register_number="21BCE0001") is True
    assert check_student_identifiers(body, register_number="22BCE0002") is False
    
    # 2. Email Address match
    assert check_student_identifiers(body, email="student@vitstudent.ac.in") is True
    assert check_student_identifiers(body, email="STUDENT@vitstudent.ac.in") is True
    assert check_student_identifiers(body, email="other@vit.edu") is False
    
    # 3. NeoPAT ID match
    assert check_student_identifiers(body, neopat_id="np0099") is True
    assert check_student_identifiers(body, neopat_id="NP0099") is True
    assert check_student_identifiers(body, neopat_id="NP1000") is False
    
    # 4. Student Name split matching
    assert check_student_identifiers(body, full_name="Hemanth Raja") is True
    assert check_student_identifiers(body, full_name="Raja Hemanth") is True  # Order independent
    assert check_student_identifiers(body, full_name="Hemanth Kumar") is False # Only 1 token matches
    assert check_student_identifiers(body, full_name="Kumar Dev") is False     # 0 tokens match
    
    # 5. Empty inputs
    assert check_student_identifiers(None) is False
    assert check_student_identifiers("") is False
