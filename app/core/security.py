import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = hashed_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = _b64url_decode(salt_text)
        expected_digest = _b64url_decode(digest_text)
    except (ValueError, TypeError):
        return False

    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    return _encode_jwt(payload)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_text, payload_text, signature_text = token.split(".", 2)
    except ValueError as exc:
        raise _credentials_error() from exc

    signed_content = f"{header_text}.{payload_text}".encode("utf-8")
    expected_signature = _sign(signed_content)
    actual_signature = _b64url_decode(signature_text)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise _credentials_error()

    try:
        payload = json.loads(_b64url_decode(payload_text))
    except (json.JSONDecodeError, ValueError) as exc:
        raise _credentials_error() from exc

    if payload.get("type") != "access":
        raise _credentials_error()

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise _credentials_error()

    return payload


def _encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    if settings.jwt_algorithm != "HS256":
        raise RuntimeError("Only HS256 JWTs are supported")

    header_text = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_text = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signed_content = f"{header_text}.{payload_text}".encode("utf-8")
    signature_text = _b64url_encode(_sign(signed_content))
    return f"{header_text}.{payload_text}.{signature_text}"


def _sign(content: bytes) -> bytes:
    return hmac.new(settings.jwt_secret_key.encode("utf-8"), content, hashlib.sha256).digest()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
