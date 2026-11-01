"""Print a new VAPID key pair for Web Push (put the private key in VAPID_PRIVATE_KEY)."""

from src.services.push.webpush import VapidKeys

if __name__ == "__main__":
    keys = VapidKeys.generate()
    print(f"VAPID_PRIVATE_KEY={keys.private_b64u}")
    print(f"# public key (served to browsers automatically): {keys.public_b64u}")
