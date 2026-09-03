import uuid
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User, PasswordResetToken, RevokedToken
from app.models.organization import Organization, OrganizationMembership


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"iat": now, "exp": expire, "jti": uuid.uuid4().hex})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        return payload
    except jwt.PyJWTError:
        return None


def hash_token(raw_token: str) -> str:
    """Hash a token string using SHA-256 for secure database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def create_password_reset_token(user_id: str, db: AsyncSession) -> str:
    """Generate a high-entropy password reset token, store its hash, and return raw token."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    reset_entry = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset_entry)
    await db.flush()
    return raw_token


async def verify_and_consume_reset_token(raw_token: str, db: AsyncSession) -> Optional[User]:
    """Verify reset token validity, mark it as consumed, and return the associated User."""
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    query = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    )
    result = await db.execute(query)
    token_obj = result.scalars().first()

    if not token_obj:
        return None

    # Mark as consumed
    token_obj.used_at = now
    await db.flush()

    user_query = select(User).where(User.id == token_obj.user_id, User.is_active == True)
    user_result = await db.execute(user_query)
    return user_result.scalars().first()


async def revoke_token(raw_token: str, user_id: Optional[str], db: AsyncSession) -> None:
    """Invalidates an active JWT session token upon logout."""
    tok_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    existing = await db.execute(select(RevokedToken).where(RevokedToken.token_hash == tok_hash))
    if not existing.scalar_one_or_none():
        revoked_entry = RevokedToken(
            token_hash=tok_hash,
            user_id=user_id,
            revoked_at=now,
            expires_at=expires_at,
        )
        db.add(revoked_entry)
        await db.commit()


async def is_token_revoked(raw_token: str, db: AsyncSession) -> bool:
    """Checks if a session token has been explicitly invalidated/logged out."""
    tok_hash = hash_token(raw_token)
    res = await db.execute(select(RevokedToken).where(RevokedToken.token_hash == tok_hash))
    return res.scalar_one_or_none() is not None
