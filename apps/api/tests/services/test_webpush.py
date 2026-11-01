"""Web Push encryption and VAPID, checked against RFC 8291 Appendix A."""

import json
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.services.push.webpush import (
    VapidKeys,
    b64u_decode,
    derive_cek_nonce,
    encrypt,
    public_bytes,
)


def key(b64u: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(b64u_decode(b64u), "big"), ec.SECP256R1())


# RFC 8291 Appendix A
UA_PRIVATE = key("q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94")
AS_PRIVATE = key("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw")
AUTH = b64u_decode("BTBZMqHH6r4Tts7J_aSIgg")
SALT = b64u_decode("DGv6ra1nlYgDCS1FRnbzlw")
PLAINTEXT = b"When I grow up, I want to be a watermelon"
EXPECTED = b64u_decode(
    "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6Tlz"
    "AC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
)


def decrypt(body: bytes, ua_private: ec.EllipticCurvePrivateKey, auth: bytes) -> bytes:
    """The receiving side, written from RFC 8188/8291, to round-trip messages."""
    salt, rs, idlen = body[:16], struct.unpack("!L", body[16:20])[0], body[20]
    as_public = body[21 : 21 + idlen]
    assert rs == 4096
    as_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public)
    ua_public = public_bytes(ua_private.public_key())
    cek, nonce = derive_cek_nonce(ua_private.exchange(ec.ECDH(), as_key), auth, ua_public, as_public, salt)
    record = AESGCM(cek).decrypt(nonce, body[21 + idlen :], None)
    assert record.endswith(b"\x02")
    return record[:-1]


def test_rfc8291_example_is_byte_exact():
    body = encrypt(PLAINTEXT, public_bytes(UA_PRIVATE.public_key()), AUTH, as_private=AS_PRIVATE, salt=SALT)
    assert body == EXPECTED


def test_rfc8291_example_decrypts():
    assert decrypt(EXPECTED, UA_PRIVATE, AUTH) == PLAINTEXT


def test_fresh_keys_round_trip():
    import os

    for _ in range(10):
        ua = ec.generate_private_key(ec.SECP256R1())
        auth = os.urandom(16)
        msg = os.urandom(500)
        assert decrypt(encrypt(msg, public_bytes(ua.public_key()), auth), ua, auth) == msg


def test_vapid_token_verifies_with_the_public_key():
    keys = VapidKeys.generate()
    again = VapidKeys.from_private(keys.private_b64u)
    assert again.public_b64u == keys.public_b64u

    header = keys.authorization("https://fcm.googleapis.com/fcm/send/abc", "mailto:ops@phoenix.test", now=1_000)
    token = header.split("t=")[1].split(",")[0]
    k = header.split("k=")[1]
    assert k == keys.public_b64u
    head, claims, sig = token.split(".")
    assert json.loads(b64u_decode(claims)) == {
        "aud": "https://fcm.googleapis.com",
        "exp": 1_000 + 12 * 3600,
        "sub": "mailto:ops@phoenix.test",
    }
    raw = b64u_decode(sig)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64u_decode(k))
    pub.verify(der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))  # raises if invalid
