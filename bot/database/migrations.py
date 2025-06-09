"""
Database migration utilities.
"""

import logging
from typing import List

from bot.database.models import DatabaseSchema

logger = logging.getLogger(__name__)

class MigrationManager:
    """Handles database migrations and schema updates."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    async def run_migrations(self):
        """Run all necessary database migrations."""
        try:
            logger.info("Starting database migrations...")
            
            # Create migration tracking table
            await self.create_migration_table()
            
            # Get current migration version
            current_version = await self.get_current_version()
            
            # Run migrations in order
            migrations = self.get_migrations()
            
            for version, migration in migrations.items():
                if version > current_version:
                    logger.info(f"Running migration version {version}")
                    await migration()
                    await self.update_version(version)
            
            logger.info("Database migrations completed successfully")
            
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            raise
    
    async def create_migration_table(self):
        """Create the migration tracking table."""
        command = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """
        await self.db_manager.execute_command(command)
    
    async def get_current_version(self) -> int:
        """Get the current migration version."""
        try:
            result = await self.db_manager.execute_query(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            if result and result[0]['version']:
                return result[0]['version']
            return 0
        except:
            return 0
    
    async def update_version(self, version: int):
        """Update the migration version."""
        await self.db_manager.execute_command(
            "INSERT INTO schema_migrations (version) VALUES ($1)",
            version
        )
    
    def get_migrations(self) -> dict:
        """Get all migration functions in order."""
        return {
            1: self.migration_001_initial_schema,
            2: self.migration_002_add_indexes,
            3: self.migration_003_add_item_suggestions,
        }
    
    async def migration_001_initial_schema(self):
        """Migration 001: Create initial database schema."""
        schema = DatabaseSchema()
        
        # Create all tables
        for table_name, create_sql in schema.get_create_statements().items():
            logger.info(f"Creating table: {table_name}")
            await self.db_manager.execute_command(create_sql)
    
    async def migration_002_add_indexes(self):
        """Migration 002: Add performance indexes."""
        schema = DatabaseSchema()
        
        # Create all indexes
        for index_sql in schema.get_index_statements():
            logger.info(f"Creating index: {index_sql}")
            await self.db_manager.execute_command(index_sql)
    
    async def migration_003_add_item_suggestions(self):
        """Migration 003: Add item suggestion features."""
        # This migration is already included in the initial schema
        # but kept as an example for future migrations
        pass

async def run_migrations(db_manager):
    """Run database migrations."""
    migration_manager = MigrationManager(db_manager)
    await migration_manager.run_migrations()
