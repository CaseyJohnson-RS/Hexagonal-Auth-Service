import pytest
import bcrypt as _bcrypt

from sqlalchemy import text

from app.adapters.outbound.persistence.sqlalchemy.models import Base
from app.infrastructure.db.postgres import engine, async_session_factory


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


@pytest.fixture(scope="function")
async def async_session():
    async with async_session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        await session.commit()
        yield session

    await engine.dispose()  # It's necessary, lol
