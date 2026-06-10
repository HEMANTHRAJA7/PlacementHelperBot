import base64
import httpx
from typing import Tuple

async def fetch_gmail_message(access_token: str, message_id: str) -> dict:
    """Fetches raw message payload from the Google Gmail API using the access token."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"}
        )
        response.raise_for_status()
        return response.json()

def parse_gmail_message(message_data: dict) -> Tuple[str, str, str]:
    """Parses subject, sender (from), and plaintext body content from a Gmail message payload.
    
    Returns:
        Tuple[subject, from_address, body_text]
    """
    headers = message_data.get("payload", {}).get("headers", [])
    
    subject = ""
    from_address = ""
    for header in headers:
        name = header.get("name", "").lower()
        if name == "subject":
            subject = header.get("value", "")
        elif name == "from":
            from_address = header.get("value", "")
            
    payload = message_data.get("payload", {})
    body = _extract_body_text(payload)
    
    # If plain text body is empty, fall back to checking if there is a HTML part we can decode
    if not body:
        body = _extract_html_fallback(payload)
        
    return subject, from_address, body

def _extract_body_text(part: dict) -> str:
    """Recursively extracts plain text content from MIME parts."""
    mime_type = part.get("mimeType", "")
    body_data = part.get("body", {}).get("data", "")
    
    if mime_type == "text/plain" and body_data:
        try:
            # Gmail uses URL-safe base64 encoding
            decoded_bytes = base64.urlsafe_b64decode(body_data.encode("utf-8"))
            return decoded_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
            
    parts = part.get("parts", [])
    body_texts = []
    for subpart in parts:
        sub_text = _extract_body_text(subpart)
        if sub_text:
            body_texts.append(sub_text)
            
    if body_texts:
        return "\n".join(body_texts)
        
    return ""

def _extract_html_fallback(part: dict) -> str:
    """Fallback to extract raw content from HTML MIME parts if no plain text part was found."""
    mime_type = part.get("mimeType", "")
    body_data = part.get("body", {}).get("data", "")
    
    if mime_type == "text/html" and body_data:
        try:
            decoded_bytes = base64.urlsafe_b64decode(body_data.encode("utf-8"))
            return decoded_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
            
    parts = part.get("parts", [])
    for subpart in parts:
        sub_text = _extract_html_fallback(subpart)
        if sub_text:
            return sub_text
            
    return ""

async def refresh_access_token(refresh_token: str) -> str:
    """Uses the refresh token to obtain a new temporary access token from Google OAuth2."""
    from src.core.config import settings
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"]

async def fetch_gmail_attachment(access_token: str, message_id: str, attachment_id: str) -> bytes:
    """Downloads a raw message attachment binary payload from the Gmail API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()
        raw_data = data.get("data", "")
        return base64.urlsafe_b64decode(raw_data.encode("utf-8"))

async def setup_gmail_watch(access_token: str, topic_name: str) -> dict:
    """Sets up a Gmail push notification watch.
    
    Returns:
        dict containing 'expiration' (string timestamp in milliseconds) and 'historyId'.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/watch",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "topicName": topic_name,
                "labelIds": ["INBOX"]
            }
        )
        response.raise_for_status()
        return response.json()



