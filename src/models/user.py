from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON, Numeric, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    gmail_address = Column(String(255), nullable=False)
    encrypted_refresh_token = Column(Text, nullable=False)
    encrypted_register_number = Column(String(512), nullable=True)
    encrypted_neopat_id = Column(String(512), nullable=True)
    watch_active = Column(Boolean, default=True, nullable=False)
    watch_resource_id = Column(String(255), nullable=True)
    watch_expiration = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")

class DeadLetterQueue(Base):
    __tablename__ = "dead_letter_queue"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), index=True, nullable=False)
    payload = Column(JSON, nullable=False)
    error_reason = Column(Text, nullable=True)
    failed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=False)
    message_id = Column(String(255), nullable=True, index=True)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    message_id = Column(String(255), nullable=True, index=True)
    resource_type = Column(String(100), nullable=True)
    error_code = Column(String(100), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), nullable=True)
    role = Column(String(255), nullable=True)
    category = Column(String(100), nullable=False)
    deadline_at = Column(DateTime(timezone=True), nullable=False)
    reminded_24h = Column(Boolean, default=False, nullable=False)
    reminded_6h = Column(Boolean, default=False, nullable=False)
    reminded_1h = Column(Boolean, default=False, nullable=False)
    last_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    source_email_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="reminders")



