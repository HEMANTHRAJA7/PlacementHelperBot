import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.config import settings
from src.core.database import Base

# Override database URL to use an in-memory SQLite database for testing
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    yield res
    res.close()

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Initialize SQLite in-memory engine and build all tables, binding global SessionLocal to it."""
    from src.core import database
    test_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Save original database references
    orig_engine = database.engine
    orig_session_local = database.SessionLocal
    
    # Dynamically patch global references
    database.engine = test_engine
    database.SessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield test_engine
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    await test_engine.dispose()
    
    # Restore original references
    database.engine = orig_engine
    database.SessionLocal = orig_session_local

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Provide a database session fixture mapping to the patched SessionLocal."""
    from src.core import database
    async with database.SessionLocal() as session:
        yield session


class MockRedis:
    """In-memory mock for async Redis operations."""
    def __init__(self):
        self.store = {}

    async def get(self, key: str) -> str:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        self.store[key] = value
        return True

    async def flushall(self):
        self.store.clear()

@pytest.fixture(scope="function")
def mock_redis():
    """Fixture to provide a clean mock Redis instance."""
    return MockRedis()
