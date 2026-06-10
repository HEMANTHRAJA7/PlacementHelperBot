import httpx
import logging
from typing import Optional, List
from src.core.config import settings

logger = logging.getLogger(__name__)

EMOJI_MAP = {
    "Offer": "🔴",
    "Shortlist": "🟡",
    "Interview": "🔵",
    "Assessment": "🟢",
    "Opportunity": "⚪"
}

def format_telegram_message(
    company: Optional[str],
    category: Optional[str],
    role: Optional[str],
    package: Optional[str],
    deadline: Optional[str],
    application_links: List[str]
) -> str:
    """Formats placement metadata into HTML for Telegram bot delivery."""
    # Normalize category capitalization to match EMOJI_MAP keys
    norm_category = category
    if category:
        # e.g., 'offer' -> 'Offer', 'OFFER' -> 'Offer'
        norm_category = category.strip().capitalize()
        
    emoji = EMOJI_MAP.get(norm_category, "⚪")
    
    lines = [
        f"<b>{emoji} Placement Update: {company or 'Unknown Company'}</b>\n",
        f"<b>Category:</b> {norm_category or 'Opportunity'}",
    ]
    
    if role:
        lines.append(f"<b>Role:</b> {role}")
    if package:
        lines.append(f"<b>Package:</b> {package}")
    if deadline:
        lines.append(f"<b>Deadline:</b> {deadline}")
        
    if application_links:
        lines.append("\n<b>Application Links:</b>")
        for i, link in enumerate(application_links, 1):
            lines.append(f"{i}. <a href=\"{link}\">Link</a>")
            
    return "\n".join(lines)

async def send_telegram_alert(
    telegram_id: int,
    text: str,
    bot_token: Optional[str] = None
) -> bool:
    """Sends a formatted HTML alert message to a student's Telegram ID silently.
    
    Returns True if successful, False otherwise.
    """
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured in settings.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": True,  # Silence alert delivery (D-14)
        "disable_web_page_preview": False
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code == 200:
                logger.info(f"Successfully sent silent Telegram notification to {telegram_id}")
                return True
            else:
                logger.error(
                    f"Failed to send Telegram message to {telegram_id}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                from src.core.metrics import TELEGRAM_DELIVERY_FAILURES
                TELEGRAM_DELIVERY_FAILURES.inc()
                return False
    except Exception as e:
        logger.error(f"HTTP request to Telegram API failed: {e}")
        from src.core.metrics import TELEGRAM_DELIVERY_FAILURES
        TELEGRAM_DELIVERY_FAILURES.inc()
        return False

