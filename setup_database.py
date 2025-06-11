
import asyncio
import logging
from bot.database.connection import DatabaseManager
from bot.database.migrations import run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_database():
    """Initialize database and run all migrations."""
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        logger.info("Running database migrations...")
        await run_migrations(db_manager)
        
        await db_manager.close()
        logger.info("Database setup completed successfully")
        
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_database())
