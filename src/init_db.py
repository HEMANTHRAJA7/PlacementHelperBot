import asyncio
import sys
from src.core.database import engine, Base
# Import models to ensure they are registered with the declarative Base
from src.models.user import User, DeadLetterQueue, AIUsageLog, AuditLog, Reminder

async def init_db():
    print("Connecting to database and creating tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Success! Database tables created successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_db())
