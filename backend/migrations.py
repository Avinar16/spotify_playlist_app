"""Database migrations - add top_artists column and bridge_artists table"""
import asyncio
from sqlalchemy import text
from app.infrastructure.database.database import engine


async def add_top_artists_column():
    """Add top_artists column to users table"""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(
            text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='top_artists'
            """)
        )
        
        if result.fetchone():
            print("✅ Column 'top_artists' already exists")
            return
        
        # Add column
        await conn.execute(
            text("""
                ALTER TABLE users 
                ADD COLUMN top_artists TEXT NULL
            """)
        )
        print("✅ Added column 'top_artists' to users table")


async def create_bridge_artists_table():
    """Create playlist_bridge_artists table"""
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(
            text("""
                SELECT EXISTS(
                    SELECT FROM information_schema.tables 
                    WHERE table_name='playlist_bridge_artists'
                )
            """)
        )
        
        if result.scalar():
            print("✅ Table 'playlist_bridge_artists' already exists")
            return
        
        # Create table
        await conn.execute(
            text("""
                CREATE TABLE playlist_bridge_artists (
                    id VARCHAR(36) PRIMARY KEY,
                    playlist_id VARCHAR(36) NOT NULL,
                    artist_name VARCHAR(255) NOT NULL,
                    score FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                    INDEX idx_playlist_id (playlist_id)
                )
            """)
        )
        print("✅ Created table 'playlist_bridge_artists'")


async def main():
    try:
        await add_top_artists_column()
        await create_bridge_artists_table()
        print("✅ All migrations completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
