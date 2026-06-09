from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from src.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    gmail_address = Column(String(255), nullable=False)
    encrypted_refresh_token = Column(Text, nullable=False)
    encrypted_register_number = Column(String(512), nullable=True)
    encrypted_neopat_id = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DeadLetterQueue(Base):
    __tablename__ = "dead_letter_queue"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), index=True, nullable=False)
    payload = Column(JSON, nullable=False)
    error_reason = Column(Text, nullable=True)
    failed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
