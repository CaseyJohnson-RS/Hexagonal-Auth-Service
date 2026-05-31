import pytest
from passlib.context import CryptContext

from sqlalchemy import text

from app.adapters.outbound.persistence.sqlalchemy.models import Base
from app.infrastructure.db.postgres import engine, async_session_factory


@pytest.fixture(scope="session", autouse=True)
def fast_hash():
    """Replace bcrypt with pbkdf2_sha256 for the test session.

    passlib 1.7.4 + bcrypt 5.x: detect_wrap_bug internally hashes a 73-byte
    password which bcrypt 5.x hard-rejects. pbkdf2_sha256 has no such limit.
    """
    import app.core.utils.security as sec
    original = sec.pwd_context
    sec.pwd_context = CryptContext(schemes=["pbkdf2_sha256"])
    yield
    sec.pwd_context = original


@pytest.fixture(scope="function")
async def async_session():
    async with async_session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        await session.commit()
        yield session

    await engine.dispose()  # It's necessary, lol

