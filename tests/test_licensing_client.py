import base64
import json
import unittest
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licensing_client import (
    LicenseVerificationError,
    offline_grace_is_valid,
    sha256_hex,
    verify_activation_response,
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


class LicenseVerificationTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_jwk = {"kty": "OKP", "crv": "Ed25519", "x": b64url(public_bytes)}
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.fingerprint_hash = sha256_hex("test-device-fingerprint")
        self.payload = {
            "schema_version": 1,
            "success": True,
            "status": "activated",
            "license_id": "test-license",
            "starts_at": (self.now - timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now + timedelta(days=30)).isoformat(),
            "device_id": "test-device",
            "device_fingerprint_hash": self.fingerprint_hash,
            "issued_at": self.now.isoformat(),
            "verify_again_after": (self.now + timedelta(days=7)).isoformat(),
            "offline_grace_until": (self.now + timedelta(days=14)).isoformat(),
        }
        self.response = self.sign_payload(self.payload)

    def sign_payload(self, payload):
        encoded = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = self.private_key.sign(encoded.encode("ascii"))
        return {
            "success": True,
            "signed_response": True,
            "algorithm": "Ed25519",
            "payload": encoded,
            "signature": b64url(signature),
        }

    def test_valid_signed_activation_is_accepted(self):
        result = verify_activation_response(
            self.response, self.public_jwk, self.fingerprint_hash, self.now
        )
        self.assertEqual(result["license_id"], "test-license")
        self.assertFalse(result["_client_online_check_due"])

    def test_tampered_payload_is_rejected(self):
        tampered = dict(self.response)
        tampered["payload"] = b64url(b'{"schema_version":1}')
        with self.assertRaises(LicenseVerificationError):
            verify_activation_response(
                tampered, self.public_jwk, self.fingerprint_hash, self.now
            )

    def test_wrong_device_is_rejected(self):
        with self.assertRaises(LicenseVerificationError):
            verify_activation_response(
                self.response, self.public_jwk, sha256_hex("another-device"), self.now
            )

    def test_license_before_start_date_is_rejected(self):
        payload = dict(self.payload)
        payload["starts_at"] = (self.now + timedelta(days=1)).isoformat()
        with self.assertRaises(LicenseVerificationError):
            verify_activation_response(
                self.sign_payload(payload), self.public_jwk, self.fingerprint_hash, self.now
            )

    def test_expired_license_is_rejected(self):
        payload = dict(self.payload)
        payload["expires_at"] = (self.now - timedelta(seconds=1)).isoformat()
        with self.assertRaises(LicenseVerificationError):
            verify_activation_response(
                self.sign_payload(payload), self.public_jwk, self.fingerprint_hash, self.now
            )

    def test_expired_offline_grace_is_rejected(self):
        payload = dict(self.payload)
        payload["offline_grace_until"] = (self.now - timedelta(seconds=1)).isoformat()
        response = self.sign_payload(payload)
        self.assertFalse(
            offline_grace_is_valid(
                response["payload"], response["signature"], self.public_jwk,
                self.fingerprint_hash, self.now
            )
        )

    def test_due_online_check_is_reported(self):
        payload = dict(self.payload)
        payload["verify_again_after"] = (self.now - timedelta(seconds=1)).isoformat()
        result = verify_activation_response(
            self.sign_payload(payload), self.public_jwk, self.fingerprint_hash, self.now
        )
        self.assertTrue(result["_client_online_check_due"])


if __name__ == "__main__":
    unittest.main()
