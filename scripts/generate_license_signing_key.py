"""Generate an Ed25519 JWK pair locally for Supabase license signing.

Run on a trusted machine. Never commit the generated private key file.
"""
import base64
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

private = Ed25519PrivateKey.generate()
private_raw = private.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption(),
)
public_raw = private.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
private_jwk = {"kty": "OKP", "crv": "Ed25519", "x": b64url(public_raw), "d": b64url(private_raw)}
public_jwk = {"kty": "OKP", "crv": "Ed25519", "x": b64url(public_raw)}
Path("license-signing-private.jwk.json").write_text(json.dumps(private_jwk), encoding="utf-8")
Path("license-signing-public.jwk.json").write_text(json.dumps(public_jwk), encoding="utf-8")
print("Created license-signing-private.jwk.json and license-signing-public.jwk.json")
print("PRIVATE KEY: add the entire private JSON file contents to Supabase Edge Function secret LICENSE_SIGNING_PRIVATE_JWK.")
print("PUBLIC KEY: embed the public JSON in the client application.")
print("Do not upload or commit the private key. Keep a secure backup; losing it requires rotating the signing key.")
