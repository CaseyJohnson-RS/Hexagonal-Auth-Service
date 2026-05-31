import pytest
import bcrypt as _bcrypt


@pytest.fixture(scope="session", autouse=True)
def fast_hash():
    """Use bcrypt rounds=4 instead of the default 12 for the test session.

    bcrypt with rounds=4 is ~200x faster than rounds=12 and still exercises
    the full hash/verify path correctly.
    """
    import app.core.utils.security as sec

    original = sec.hash_password

    def _fast_hash(password: str) -> str:
        return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=4)).decode()

    sec.hash_password = _fast_hash
    yield
    sec.hash_password = original
