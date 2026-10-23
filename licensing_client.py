"""Client-side verification helpers for signed Database Yedekle licenses."""
from __future__ import annotations
import base64, hashlib, json
from datetime import datetime, timezone
from typing import Any, Mapping
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

class LicenseVerificationError(ValueError):
    """Raised when a signed license response is invalid or expired."""

def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise LicenseVerificationError("Missing base64url value")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise LicenseVerificationError("Invalid base64url value") from exc

def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def verify_activation_response(response: Mapping[str, Any], public_jwk: Mapping[str, Any],
                               expected_device_fingerprint_hash: str,
                               now: datetime | None = None) -> dict[str, Any]:
    """Verify Ed25519 signature and security-relevant license claims."""
    if response.get("success") is not True or response.get("signed_response") is not True:
        raise LicenseVerificationError("Server did not return a signed success response")
    if response.get("algorithm") != "Ed25519":
        raise LicenseVerificationError("Unsupported signature algorithm")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(_b64url_decode(str(public_jwk["x"])))
        encoded = str(response["payload"])
        public_key.verify(_b64url_decode(str(response["signature"])), encoded.encode("ascii"))
        payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
    except LicenseVerificationError:
        raise
    except Exception as exc:
        raise LicenseVerificationError("Signature or payload verification failed") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise LicenseVerificationError("Unsupported license payload")
    if payload.get("success") is not True:
        raise LicenseVerificationError("License was not approved")
    if payload.get("status") not in ("activated", "already_activated"):
        raise LicenseVerificationError("License is not active")
    if payload.get("device_fingerprint_hash") != expected_device_fingerprint_hash:
        raise LicenseVerificationError("License belongs to a different device")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    def parse_time(name: str, required: bool = True):
        raw = payload.get(name)
        if raw is None and not required:
            return None
        if not isinstance(raw, str):
            raise LicenseVerificationError(f"Missing {name}")
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        except Exception as exc:
            raise LicenseVerificationError(f"Invalid {name}") from exc
    issued = parse_time("issued_at")
    verify_again = parse_time("verify_again_after")
    grace_until = parse_time("offline_grace_until")
    starts = parse_time("starts_at", required=False)
    expiry = parse_time("expires_at", required=False)
    if issued and issued > current.replace(microsecond=0):
        raise LicenseVerificationError("License response is from the future")
    if starts and current < starts:
        raise LicenseVerificationError("License is not active yet")
    if expiry and current >= expiry:
        raise LicenseVerificationError("License has expired")
    if grace_until and current >= grace_until:
        raise LicenseVerificationError("Offline grace period has ended")
    payload["_client_online_check_due"] = bool(verify_again and current >= verify_again)
    return payload

def offline_grace_is_valid(encoded_payload: str, signature: str, public_jwk: Mapping[str, Any],
                            expected_device_fingerprint_hash: str,
                            now: datetime | None = None) -> bool:
    """Verify a cached signed envelope during the temporary offline grace period."""
    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
        envelope = {"success": True, "signed_response": True, "algorithm": "Ed25519",
                    "payload": encoded_payload, "signature": signature}
        verify_activation_response(envelope, public_jwk, expected_device_fingerprint_hash, now)
        return bool(payload.get("offline_grace_until"))
    except (LicenseVerificationError, ValueError, TypeError):
        return False
