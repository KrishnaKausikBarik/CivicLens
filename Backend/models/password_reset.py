from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String

from database import db


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = db.Column(
        BigInteger().with_variant(db.Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = db.Column(String(64), nullable=False, unique=True)
    expires_at = db.Column(DateTime(timezone=True), nullable=False)
    used_at = db.Column(DateTime(timezone=True), nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=db.func.now())

    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )


class PasswordResetRateLimit(db.Model):
    __tablename__ = "password_reset_rate_limits"

    identifier_hash = db.Column(String(64), primary_key=True)
    window_started_at = db.Column(DateTime(timezone=True), nullable=False)
    attempts = db.Column(Integer, nullable=False, default=1)

    __table_args__ = (Index("ix_password_reset_rate_limits_window", "window_started_at"),)
