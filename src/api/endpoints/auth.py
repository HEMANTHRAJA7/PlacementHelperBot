import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from google_auth_oauthlib.flow import Flow

from src.core.config import settings
from src.core.database import get_db
from src.core.security import CredentialEncryptor
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

def get_oauth_flow() -> Flow:
    """Helper to initialize the OAuth Flow using the client config and scopes."""
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        # Enforce Least Privilege: ONLY read-only Gmail scope requested
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

@router.get("/login")
def login(tg_id: int = Query(..., description="The user's Telegram ID")):
    """Initiates Google OAuth2 consent flow, mapping user's Telegram ID via state."""
    flow = get_oauth_flow()
    # prompt="consent" forces Google to return refresh_token on every connection
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(tg_id),
        prompt="consent"
    )
    return RedirectResponse(authorization_url)

@router.get("/callback", response_class=HTMLResponse)
async def callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="Telegram ID mapped from login state"),
    db: AsyncSession = Depends(get_db)
):
    """Exchanges code for credentials, fetches email, encrypts secrets, and saves to database."""
    try:
        telegram_id = int(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter; Telegram ID must be an integer"
        )

    flow = get_oauth_flow()
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error(f"Error exchanging authorization code: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth exchange failed: {str(e)}"
        )

    credentials = flow.credentials
    if not credentials.refresh_token:
        logger.error(f"Failed to retrieve refresh token for Telegram ID: {telegram_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Did not receive refresh token. Please revoke access from Google Account Settings and retry."
        )

    # Fetch email address from the Gmail profile endpoint to adhere to Least Privilege rule
    async with httpx.AsyncClient() as client:
        try:
            profile_response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {credentials.token}"}
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
            gmail_address = profile.get("emailAddress")
            if not gmail_address:
                raise ValueError("emailAddress field missing from Google profile response")
        except Exception as e:
            logger.error(f"Failed to fetch Gmail profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch email address from Gmail API"
            )

    encryptor = CredentialEncryptor()
    encrypted_token = encryptor.encrypt(credentials.refresh_token)

    # Check if user already exists
    result = await db.execute(select(User).filter_by(telegram_id=telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            gmail_address=gmail_address,
            encrypted_refresh_token=encrypted_token
        )
        db.add(user)
    else:
        user.gmail_address = gmail_address
        user.encrypted_refresh_token = encrypted_token

    await db.commit()

    # Premium success landing page
    success_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Connection Success | Placement Sentinel</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #09090b;
                --card-bg: #18181b;
                --primary: #10b981;
                --text: #fafafa;
                --text-muted: #a1a1aa;
                --border: #27272a;
            }
            body {
                margin: 0;
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                overflow: hidden;
            }
            .container {
                background: var(--card-bg);
                border: 1px solid var(--border);
                padding: 2.5rem;
                border-radius: 16px;
                text-align: center;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                transform: translateY(20px);
                animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            }
            @keyframes slideUp {
                to { transform: translateY(0); }
            }
            .icon-wrapper {
                width: 72px;
                height: 72px;
                background: rgba(16, 185, 129, 0.1);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1.5rem auto;
            }
            .icon {
                color: var(--primary);
                font-size: 2.5rem;
                font-weight: bold;
            }
            h1 {
                font-size: 1.8rem;
                margin: 0 0 0.5rem 0;
                font-weight: 600;
            }
            p {
                color: var(--text-muted);
                line-height: 1.5;
                font-size: 1rem;
                margin: 0 0 2rem 0;
            }
            .badge {
                display: inline-block;
                background: #27272a;
                border: 1px solid var(--border);
                padding: 0.5rem 1rem;
                border-radius: 8px;
                font-family: monospace;
                font-size: 0.9rem;
                color: var(--primary);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon-wrapper">
                <div class="icon">✓</div>
            </div>
            <h1>Connection Secure</h1>
            <p>Placement Sentinel has successfully authenticated your account. Your credentials are encrypted and stored securely.</p>
            <div class="badge">""" + gmail_address + """</div>
        </div>
    </body>
    </html>
    """
    return success_html
