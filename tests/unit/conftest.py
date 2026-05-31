import pytest
from passlib.context import CryptContext


@pytest.fixture(scope="session", autouse=True)
def fast_hash():
    """Swap bcrypt for pbkdf2_sha256 for the entire unit test session.

    passlib 1.7.4 is incompatible with bcrypt >=5.x (the wrap-bug detection
    probe exceeds bcrypt's new 72-byte hard limit). pbkdf2_sha256 is pure
    Python, requires no native library, and is ~100x faster — the hash/verify
    round-trip still works correctly because both operations go through the
    same patched context.
    """
    import app.core.utils.security as sec

    original = sec.pwd_context
    sec.pwd_context = CryptContext(schemes=["pbkdf2_sha256"])
    yield
    sec.pwd_context = original
