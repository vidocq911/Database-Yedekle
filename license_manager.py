"""Online activation and signed offline-cache support for Database Yedekle."""
from __future__ import annotations

import json
import os
import platform
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from licensing_client import LicenseVerificationError, sha256_hex, verify_activation_response

SUPABASE_URL = "https://hkuoymftockxmynrcjwh.supabase.co"
ACTIVATE_URL = SUPABASE_URL + "/functions/v1/activate-license"


def _resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def _config_dir() -> Path:
    root = Path(os.getenv("APPDATA", str(Path.home())))
    folder = root / "DatabaseYedekle"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _public_jwk() -> dict[str, Any]:
    candidates = [
        _resource_dir() / "license-public-jwk.json",
        Path(sys.executable).parent / "license-public-jwk.json",
    ]
    for path in candidates:
        if path.is_file():
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(value, dict) and value.get("kty") == "OKP" and value.get("crv") == "Ed25519" and isinstance(value.get("x"), str):
                return value
            raise ValueError("Lisans açık anahtarı dosyası geçersiz.")
    raise FileNotFoundError("Lisans doğrulama açık anahtarı henüz uygulama paketine eklenmemiş.")


def device_fingerprint() -> str:
    """Stable per-Windows-install identifier; never includes the user's name."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            if isinstance(machine_guid, str) and machine_guid.strip():
                return "database-yedekle:v1:" + machine_guid.strip().lower()
        except OSError:
            pass
    return "database-yedekle:v1:" + platform.node().strip().lower()


def activate(license_key: str) -> dict[str, Any]:
    key = license_key.strip()
    if not key:
        raise ValueError("Lisans anahtarını gir.")
    fingerprint = device_fingerprint()
    body = json.dumps({
        "license_key": key,
        "device_fingerprint": fingerprint,
        "device_label": platform.node()[:120],
    }).encode("utf-8")
    request = urllib.request.Request(
        ACTIVATE_URL,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            envelope = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8"))
            code = details.get("error", "activation_failed")
        except Exception:
            code = "activation_failed"
        messages = {
            "invalid_license": "Lisans anahtarı bulunamadı veya geçersiz.",
            "device_conflict": "Bu lisans başka bir cihaza bağlı. Yönetici cihaz bağlantısını kaldırmalı.",
            "customer_inactive": "Müşteri hesabı aktif değil.",
            "license_signing_not_configured": "Lisans sunucusunun imza anahtarı henüz yapılandırılmamış.",
            "license_signing_failed": "Sunucu lisans imzasını oluşturamadı.",
        }
        raise RuntimeError(messages.get(code, f"Lisans etkinleştirilemedi ({code}).")) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Lisans sunucusuna bağlanılamadı. İnternet bağlantını kontrol et.") from exc
    verified = verify_activation_response(
        envelope, _public_jwk(), sha256_hex(fingerprint)
    )
    cache = {
        "envelope": envelope,
        "device_fingerprint_hash": sha256_hex(fingerprint),
        "verified_at": verified["issued_at"],
    }
    (_config_dir() / "license-cache.json").write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return verified


def check_cached_license() -> dict[str, Any]:
    path = _config_dir() / "license-cache.json"
    if not path.is_file():
        raise FileNotFoundError("Bu bilgisayarda etkinleştirilmiş lisans bulunamadı.")
    cache = json.loads(path.read_text(encoding="utf-8"))
    fingerprint_hash = sha256_hex(device_fingerprint())
    if cache.get("device_fingerprint_hash") != fingerprint_hash:
        raise LicenseVerificationError("Kayıtlı lisans başka bir bilgisayara ait.")
    payload = verify_activation_response(
        cache["envelope"], _public_jwk(), fingerprint_hash
    )
    return payload
