import base64
import hashlib
import hmac
import os
import secrets


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEY_LENGTH = 64
DUMMY_PASSWORD_HASH = (
    "scrypt$16384$8$1$MDAwMDAwMDAwMDAwMDAwMA=="
    "$JvUn36vqhyYC+Zp5O0L+IEzFbmH8Z9L7RcHiFUy4vXvY9aw7MCTvukcbPfLQKkRk"
    "jw7HHtmws28fzAWf3qz3bQ=="
)


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_LENGTH,
    )
    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_value, digest_value = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.b64decode(salt_value)
        expected_digest = base64.b64decode(digest_value)
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(actual_digest, expected_digest)


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
