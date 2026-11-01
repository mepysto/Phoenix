"""Minimal Web Push sender: RFC 8291 payload encryption + RFC 8292 VAPID.

Implemented on `cryptography` alone: the usual Python packages either pull
in two extra HTTP stacks or only ship as legacy source builds. Verified by a
byte-exact test against the RFC 8291 Appendix A example.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RECORD_SIZE = 4096


def b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def public_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def derive_cek_nonce(
    ecdh_secret: bytes, auth_secret: bytes, ua_public: bytes, as_public: bytes, salt: bytes
) -> tuple[bytes, bytes]:
    """RFC 8291 §3.4 key combination, then RFC 8188 §2.2 key and nonce."""
    prk_key = _hmac(auth_secret, ecdh_secret)
    ikm = _hmac(prk_key, b"WebPush: info\x00" + ua_public + as_public + b"\x01")
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    return cek, nonce


def encrypt(
    plaintext: bytes,
    ua_public: bytes,
    auth_secret: bytes,
    *,
    as_private: ec.EllipticCurvePrivateKey | None = None,
    salt: bytes | None = None,
) -> bytes:
    """Encrypt one push message as a single aes128gcm record.

    `as_private` and `salt` are only passed in tests; normally both are
    fresh for every message.
    """
    if len(auth_secret) != 16 or len(ua_public) != 65:
        raise ValueError("Invalid subscription keys")
    if len(plaintext) + 1 + 16 > RECORD_SIZE:
        raise ValueError("Payload too large for one record")
    as_private = as_private or ec.generate_private_key(ec.SECP256R1())
    salt = salt or os.urandom(16)
    as_public = public_bytes(as_private.public_key())
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    cek, nonce = derive_cek_nonce(as_private.exchange(ec.ECDH(), ua_key), auth_secret, ua_public, as_public, salt)
    # 0x02 marks the last (here: only) record
    ciphertext = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)
    header = salt + struct.pack("!L", RECORD_SIZE) + bytes([len(as_public)]) + as_public
    return header + ciphertext


@dataclass(frozen=True)
class VapidKeys:
    private_key: ec.EllipticCurvePrivateKey

    @classmethod
    def from_private(cls, b64u: str) -> VapidKeys:
        value = int.from_bytes(b64u_decode(b64u), "big")
        return cls(ec.derive_private_key(value, ec.SECP256R1()))

    @classmethod
    def generate(cls) -> VapidKeys:
        return cls(ec.generate_private_key(ec.SECP256R1()))

    @property
    def private_b64u(self) -> str:
        return b64u_encode(self.private_key.private_numbers().private_value.to_bytes(32, "big"))

    @property
    def public_b64u(self) -> str:
        """The application server key browsers subscribe with."""
        return b64u_encode(public_bytes(self.private_key.public_key()))

    def authorization(self, endpoint: str, subject: str, now: int | None = None, ttl: int = 12 * 3600) -> str:
        """RFC 8292 `Authorization: vapid t=..., k=...` for the endpoint's origin."""
        parts = urlsplit(endpoint)
        claims = {"aud": f"{parts.scheme}://{parts.netloc}", "exp": (now or int(time.time())) + ttl, "sub": subject}
        signing_input = (
            b64u_encode(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
            + "."
            + b64u_encode(json.dumps(claims, separators=(",", ":")).encode())
        )
        der = self.private_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        token = signing_input + "." + b64u_encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        return f"vapid t={token}, k={self.public_b64u}"


def push_request(
    endpoint: str, p256dh: str, auth: str, payload: dict, keys: VapidKeys, subject: str, ttl: int = 3600
) -> tuple[dict[str, str], bytes]:
    """Headers and body for POSTing one notification to a push service."""
    body = encrypt(json.dumps(payload, separators=(",", ":")).encode(), b64u_decode(p256dh), b64u_decode(auth))
    headers = {
        "Authorization": keys.authorization(endpoint, subject),
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(ttl),
        "Urgency": "high",
    }
    return headers, body
