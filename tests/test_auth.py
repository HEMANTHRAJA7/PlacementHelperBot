import pytest
import base64
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.future import select
from src.core.security import CredentialEncryptor
from src.models.user import User
from src.main import app
from src.core.database import get_db

# Create a FastAPI test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def override_db_dependency(db_session):
    """Automatically override get_db dependency for tests to use the in-memory SQLite session."""
    async def _get_db_override():
        yield db_session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()

def test_credential_encryptor_keys():
    """Verify that a valid key works and an invalid key size raises a ValueError."""
    valid_key = base64.urlsafe_b64encode(b"0" * 32).decode()
    encryptor = CredentialEncryptor(valid_key)
    assert encryptor is not None

    with pytest.raises(ValueError):
        CredentialEncryptor("invalid_key_length")

def test_credential_encryptor_encryption():
    """Verify that plaintext is encrypted to a different value and decrypted accurately."""
    encryptor = CredentialEncryptor()
    secret = "my_super_secret_refresh_token"

    ciphertext = encryptor.encrypt(secret)
    assert ciphertext != secret
    assert "my_super_secret" not in ciphertext

    decrypted = encryptor.decrypt(ciphertext)
    assert decrypted == secret

@pytest.mark.asyncio
async def test_db_encryption(db_session):
    """Verify that credentials can be saved to and decrypted from the database."""
    encryptor = CredentialEncryptor()
    raw_token = "google_refresh_token_123"
    encrypted_token = encryptor.encrypt(raw_token)

    # Create and add a new user to the session
    user = User(
        telegram_id=987654321,
        gmail_address="student@vit.edu",
        encrypted_refresh_token=encrypted_token,
        encrypted_register_number=encryptor.encrypt("21BCE0001"),
        encrypted_neopat_id=encryptor.encrypt("NEOPAT123")
    )
    db_session.add(user)
    await db_session.commit()

    # Query the user back from the database
    result = await db_session.execute(select(User).filter_by(telegram_id=987654321))
    db_user = result.scalar_one()

    # Assert retrieved encrypted content matches
    assert db_user.gmail_address == "student@vit.edu"
    assert db_user.encrypted_refresh_token == encrypted_token

    # Assert successfully decrypted plaintext matches
    assert encryptor.decrypt(db_user.encrypted_refresh_token) == raw_token
    assert encryptor.decrypt(db_user.encrypted_register_number) == "21BCE0001"
    assert encryptor.decrypt(db_user.encrypted_neopat_id) == "NEOPAT123"

@patch("src.api.endpoints.auth.get_oauth_flow")
def test_oauth_login_redirect(mock_get_flow):
    """Verify GET /auth/login builds authorization URL and redirects successfully."""
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?client_id=123", "state")
    mock_get_flow.return_value = mock_flow

    response = client.get("/api/v1/auth/login?tg_id=987654321", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/auth")

@pytest.mark.asyncio
@patch("src.api.endpoints.auth.get_oauth_flow")
@patch("httpx.AsyncClient.get")
async def test_oauth_callback_success(mock_httpx_get, mock_get_flow, db_session):
    """Verify GET /auth/callback exchanges code, fetches profile, encrypts token and redirects to success landing page."""
    # Mock OAuth flow credentials return values
    mock_flow = MagicMock()
    mock_credentials = MagicMock()
    mock_credentials.refresh_token = "valid_google_refresh_token"
    mock_credentials.token = "valid_google_access_token"
    mock_flow.credentials = mock_credentials
    mock_get_flow.return_value = mock_flow

    # Mock google profile retrieval endpoint
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"emailAddress": "user@vitstudent.ac.in"}
    mock_httpx_get.return_value = mock_response

    response = client.get("/api/v1/auth/callback?code=mock_code&state=987654321")
    assert response.status_code == 200
    assert "Connection Secure" in response.text
    assert "user@vitstudent.ac.in" in response.text

    # Verify database entry has been saved and is encrypted
    result = await db_session.execute(select(User).filter_by(telegram_id=987654321))
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.gmail_address == "user@vitstudent.ac.in"
    
    encryptor = CredentialEncryptor()
    assert encryptor.decrypt(db_user.encrypted_refresh_token) == "valid_google_refresh_token"

@patch("src.api.endpoints.auth.get_oauth_flow")
def test_oauth_callback_fail_on_missing_refresh_token(mock_get_flow):
    """Verify GET /auth/callback raises 400 Bad Request if no refresh token is returned."""
    mock_flow = MagicMock()
    mock_credentials = MagicMock()
    mock_credentials.refresh_token = None
    mock_flow.credentials = mock_credentials
    mock_get_flow.return_value = mock_flow

    response = client.get("/api/v1/auth/callback?code=mock_code&state=987654321")
    assert response.status_code == 400
    assert "Did not receive refresh token" in response.json()["detail"]
