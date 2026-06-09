from cryptography.fernet import Fernet
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, status
from src.core.config import settings

class CredentialEncryptor:
    """AES-256 Fernet cryptographic wrapper for encrypting secrets in PostgreSQL."""
    def __init__(self, key: str = None):
        if not key:
            key = settings.AES_SECRET_KEY
        self.fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plain text to base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext back to plain text."""
        if not ciphertext:
            return ""
        return self.fernet.decrypt(ciphertext.encode()).decode()

def verify_pubsub_jwt(authorization: str) -> dict:
    """Verify that the OIDC token in the authorization header is signed by Google.
    
    Verifies issuer is accounts.google.com and audience matches configured webhook URL.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token structure"
        )
    
    token = authorization.split(" ")[1]
    try:
        # Verify the OIDC token using Google's verification library
        # In a real environment, this fetches Google's public certs and verifies the signature.
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=settings.WEBHOOK_AUDIENCE
        )
        
        # Verify the token issuer
        if claims.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid issuer claim")
            
        return claims
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google OIDC verification failed: {str(e)}"
        )

