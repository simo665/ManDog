
"""Database migration utilities."""

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
            4: self.update_transactions_schema,
            5: self.add_ratings_table,
            6: self.add_guild_rating_configs,
            7: self.add_listing_queues_table,
            8: self.add_items_table,
            9: self.add_scheduled_events_table,
            10: self.add_event_confirmations_table,
            11: self.add_event_ratings_table,
            12: self.add_guild_rating_configs_table,
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

    async def update_transactions_schema(self):
        """Update transactions table schema."""
        commands = [
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS item VARCHAR(200)",
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS zone VARCHAR(50)",
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS quantity INTEGER DEFAULT 1",
            "ALTER TABLE transactions ALTER COLUMN listing_id DROP NOT NULL",
        ]
        for command in commands:
            await self.db_manager.execute_command(command)

    async def add_ratings_table(self):
        """Add ratings table for new rating system."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                rater_id BIGINT NOT NULL,
                rated_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                order_id VARCHAR(100),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                status VARCHAR(20) DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected')),
                admin_id BIGINT,
                admin_notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                reviewed_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (rater_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (rated_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)

    async def add_guild_rating_configs(self):
        """Add guild rating configuration table."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS guild_rating_configs (
                guild_id BIGINT PRIMARY KEY,
                admin_channel_id BIGINT,
                low_rating_threshold INTEGER DEFAULT 3,
                require_admin_approval BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id) ON DELETE CASCADE
            )
        """)

    async def add_listing_queues_table(self):
        """Add listing queues table for WTS All Items queue functionality."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS listing_queues (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                item_name VARCHAR(200) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(listing_id, user_id, item_name)
            )
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_listing_queues_listing_id
            ON listing_queues(listing_id)
        """)
        
        logger.info("Listing queues table and index created successfully")

    async def add_items_table(self):
        """Add items table for marketplace items."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                zone TEXT NOT NULL,
                monster_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                added_by TEXT DEFAULT 'Simo',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_items_zone ON items(zone)
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_items_monster ON items(monster_name)
        """)
        
        # Populate with initial data
        await self.populate_items_table()
        
        logger.info("Items table created and populated successfully")

    async def add_scheduled_events_table(self):
        """Add scheduled_events table for event scheduling."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS scheduled_events (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
                event_time TIMESTAMPTZ NOT NULL,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'cancelled')),
                event_type VARCHAR(50) DEFAULT 'listing_reminder',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                processed_at TIMESTAMPTZ
            )
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_events_time ON scheduled_events(event_time)
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_events_status ON scheduled_events(status)
        """)
        
        logger.info("Scheduled events table created successfully")

    async def add_event_confirmations_table(self):
        """Add event_confirmations table for event participation tracking."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS event_confirmations (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                role VARCHAR(10) NOT NULL CHECK (role IN ('seller', 'buyer')),
                confirmed BOOLEAN NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (event_id) REFERENCES scheduled_events(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(event_id, user_id)
            )
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_event_confirmations_event ON event_confirmations(event_id)
        """)
        
        logger.info("Event confirmations table created successfully")

    async def add_event_ratings_table(self):
        """Add event_ratings table for event rating system."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS event_ratings (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                rater_id BIGINT NOT NULL,
                seller_id BIGINT NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (event_id) REFERENCES scheduled_events(id) ON DELETE CASCADE,
                FOREIGN KEY (rater_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (seller_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(event_id, rater_id)
            )
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_event_ratings_event ON event_ratings(event_id)
        """)
        
        await self.db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_event_ratings_seller ON event_ratings(seller_id)
        """)
        
        logger.info("Event ratings table created successfully")

    async def add_guild_rating_configs_table(self):
        """Add guild_rating_configs table for rating moderation settings."""
        await self.db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS guild_rating_configs (
                guild_id BIGINT PRIMARY KEY,
                admin_channel_id BIGINT,
                low_rating_threshold INTEGER DEFAULT 3 CHECK (low_rating_threshold >= 1 AND low_rating_threshold <= 5),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        logger.info("Guild rating configs table created successfully")

    async def populate_items_table(self):
        """Populate items table with initial marketplace data."""
        items_data = [
            # Sky items
            ('sky', 'Kirin', 'Shining Cloth'),
            ('sky', 'Kirin', 'Kirin\'s Osode'),
            ('sky', 'Kirin', 'Kirin\'s Pole'),
            ('sky', 'Suzaku', 'Suzaku\'s Sune-ate'),
            ('sky', 'Suzaku', 'Crimson Blade'),
            ('sky', 'Suzaku', 'Peacock Charm'),
            ('sky', 'Seiryu', 'Seiryu\'s Kote'),
            ('sky', 'Seiryu', 'Cobalt Blade'),
            ('sky', 'Seiryu', 'Peacock Amulet'),
            ('sky', 'Genbu', 'Genbu\'s Shield'),
            ('sky', 'Genbu', 'Speed Belt'),
            ('sky', 'Byakko', 'Byakko\'s Haidate'),
            ('sky', 'Byakko', 'Justice Badge'),
            
            # Sea items
            ('sea', 'Jailer of Hope', 'Hope Torque'),
            ('sea', 'Jailer of Hope', 'Novio Earring'),
            ('sea', 'Jailer of Hope', 'Brutal Earring'),
            ('sea', 'Jailer of Justice', 'Suppanomimi'),
            ('sea', 'Jailer of Justice', 'Ethereal Earring'),
            ('sea', 'Jailer of Faith', 'Faith Torque'),
            ('sea', 'Jailer of Faith', 'Magnetic Earring'),
            ('sea', 'Jailer of Faith', 'Hollow Earring'),
            ('sea', 'Jailer of Fortitude', 'Fortitude Torque'),
            ('sea', 'Jailer of Fortitude', 'Infernal Earring'),
            ('sea', 'Jailer of Fortitude', 'Coral Earring'),
            ('sea', 'Absolute Virtue', 'Virtue Stone'),
            
            # Dynamis items
            ('dynamis', 'Dynamis - Bastok', 'Hydra Corps'),
            ('dynamis', 'Dynamis - Bastok', 'Hydra Salade'),
            ('dynamis', 'Dynamis - San d\'Oria', 'Temple Crown'),
            ('dynamis', 'Dynamis - San d\'Oria', 'Temple Cyclas'),
            ('dynamis', 'Dynamis - Windurst', 'Sorcerer\'s Petasos'),
            ('dynamis', 'Dynamis - Windurst', 'Sorcerer\'s Coat'),
            ('dynamis', 'Dynamis - Jeuno', 'Apocalypse'),
            ('dynamis', 'Dynamis - Jeuno', 'Ragnarok'),
            ('dynamis', 'Dynamis - Jeuno', 'Redemption'),
            ('dynamis', 'Currency', '100 Byne Bills'),
            ('dynamis', 'Currency', '1 Montiont Silverpiece'),
            ('dynamis', 'Currency', '1 Ranperre\'s Goldpiece'),
            ('dynamis', 'Currency', '1 Lungo-Nango Jadeshell'),
            
            # Limbus items
            ('limbus', 'Temenos', 'Homam Zucchetto'),
            ('limbus', 'Temenos', 'Homam Corazza'),
            ('limbus', 'Temenos', 'Homam Manopolas'),
            ('limbus', 'Temenos', 'Homam Cosciales'),
            ('limbus', 'Temenos', 'Homam Gambieras'),
            ('limbus', 'Apollyon', 'Nashira Turban'),
            ('limbus', 'Apollyon', 'Nashira Manteel'),
            ('limbus', 'Apollyon', 'Nashira Gages'),
            ('limbus', 'Apollyon', 'Nashira Seraweels'),
            ('limbus', 'Apollyon', 'Nashira Crackows'),
            ('limbus', 'Omega', 'Omega\'s Eye'),
            ('limbus', 'Ultima', 'Ultima\'s Cerebrum'),
            ('limbus', 'Currency', 'Ancient Beastcoin'),
            
            # Others items
            ('others', 'Einherjar', 'Gleipnir'),
            ('others', 'Einherjar', 'Gungnir'),
            ('others', 'Einherjar', 'Defending Ring'),
            ('others', 'Einherjar', 'Amanomurakumo'),
            ('others', 'Salvage', 'Usukane Gear'),
            ('others', 'Salvage', 'Serafim Gear'),
            ('others', 'Salvage', 'Morrigan Gear'),
            ('others', 'Salvage', 'Skadi Gear'),
            ('others', 'Salvage', '35 Piece'),
            ('others', 'Salvage', '15 Piece'),
            ('others', 'Salvage', 'Alexandrite'),
            ('others', 'HNMs', 'Ridill'),
            ('others', 'HNMs', 'Kraken Club'),
            ('others', 'HNMs', 'Herald\'s Gaiters'),
            ('others', 'HNMs', 'Crimson Cuisses'),
            ('others', 'Crafting', 'Damascus Ingot'),
            ('others', 'Crafting', 'Wootz Ore'),
            ('others', 'Crafting', 'Voidstone'),
            ('others', 'Crafting', 'Dragon Heart'),
        ]
        
        for zone, monster, item in items_data:
            await self.db_manager.execute_command(
                "INSERT INTO items (zone, monster_name, item_name) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                zone, monster, item
            )

async def create_reputation_tables(db_manager):
    """Create reputation system tables."""
    try:
        # User reputation ratings
        await db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS user_ratings (
                id SERIAL PRIMARY KEY,
                rater_id BIGINT NOT NULL,
                target_id BIGINT NOT NULL,
                listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(rater_id, target_id, listing_id)
            )
        """)

        # User reputation summary
        await db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS user_reputation (
                user_id BIGINT PRIMARY KEY,
                average_rating DECIMAL(3,2) DEFAULT 0.00,
                total_ratings INTEGER DEFAULT 0,
                activity_score INTEGER DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        logger.info("Reputation tables created successfully")
    except Exception as e:
        logger.error(f"Error creating reputation tables: {e}")
        raise

async def create_listing_queues_table(db_manager):
    """Create listing queues table for All Items WTS listings."""
    try:
        await db_manager.execute_command("""
            CREATE TABLE IF NOT EXISTS listing_queues (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                item_name VARCHAR(200) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(listing_id, user_id, item_name)
            )
        """)

        # Create index for faster lookups
        await db_manager.execute_command("""
            CREATE INDEX IF NOT EXISTS idx_listing_queues_listing_id 
            ON listing_queues(listing_id)
        """)

        logger.info("Listing queues table created successfully")
    except Exception as e:
        logger.error(f"Error creating listing queues table: {e}")
        raise

async def run_migrations(db_manager):
    """Run database migrations."""
    migration_manager = MigrationManager(db_manager)
    await migration_manager.run_migrations()
