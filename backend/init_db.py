"""Initialize database - create all tables from models"""
import asyncio
from sqlalchemy import text
from app.infrastructure.database.database import engine
from app.infrastructure.database.models import Base
 
 
async def init_db():
    """Create all tables defined in models"""
    async with engine.begin() as conn:
         # Create all tables from SQLAlchemy models
        await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables created successfully")
 
 
async def main():
    try:
        await init_db()
        print("✅ Database initialization completed successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
 
 
if __name__ == "__main__":
    asyncio.run(main())
