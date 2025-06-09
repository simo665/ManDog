"""
Database connection and management utilities.
"""

import asyncio
import logging
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                rows = await connection.fetch(query, *args)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return status."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                result = await connection.execute(command, *args)
                return result
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise
    
    async def store_guild_setup(self, guild_id: int, channels: List):
        """Store guild setup information."""
        try:
            command = """
                INSERT INTO guild_configs (guild_id, setup_complete, setup_date)
                VALUES ($1, TRUE, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET setup_complete = TRUE, setup_date = $2
            """
            await self.execute_command(command, guild_id, datetime.now(timezone.utc))
            
            # Store channel information
            for channel in channels:
                await self.store_channel_info(guild_id, channel)
                
        except Exception as e:
            logger.error(f"Error storing guild setup: {e}")
            raise
    
    async def store_channel_info(self, guild_id: int, channel):
        """Store marketplace channel information."""
        try:
            # Determine channel type and zone from channel name
            channel_name = channel.name.lower()
            if "wts" in channel_name or "🔸" in channel_name:
                listing_type = "WTS"
            elif "wtb" in channel_name or "🔹" in channel_name:
                listing_type = "WTB"
            else:
                listing_type = "UNKNOWN"
            
            # Extract zone from channel name
            zone = channel_name.split("-")[-1] if "-" in channel_name else "unknown"
            
            command = """
                INSERT INTO marketplace_channels (guild_id, channel_id, listing_type, zone)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (channel_id) 
                DO UPDATE SET listing_type = $3, zone = $4
            """
            await self.execute_command(command, guild_id, channel.id, listing_type, zone)
            
        except Exception as e:
            logger.error(f"Error storing channel info: {e}")
            raise
    
    async def store_marketplace_message(self, guild_id: int, channel_id: int, message_id: int, listing_type: str, zone: str):
        """Store marketplace persistent message information."""
        try:
            command = """
                UPDATE marketplace_channels 
                SET message_id = $1 
                WHERE guild_id = $2 AND channel_id = $3
            """
            await self.execute_command(command, message_id, guild_id, channel_id)
            
        except Exception as e:
            logger.error(f"Error storing marketplace message: {e}")
            raise
    
    async def create_listing(self, user_id: int, guild_id: int, listing_type: str, zone: str, 
                           subcategory: str, item: str, quantity: int, notes: str, 
                           scheduled_time: datetime) -> Optional[int]:
        """Create a new marketplace listing."""
        try:
            # Ensure user exists in users table first
            await self.ensure_user_exists(user_id)
            
            command = """
                INSERT INTO listings (
                    user_id, guild_id, listing_type, zone, subcategory, 
                    item, quantity, notes, scheduled_time, created_at, expires_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """
            
            created_at = datetime.now(timezone.utc)
            from datetime import timedelta
            expires_at = created_at + timedelta(days=14)  # 14 days expiry
            
            result = await self.execute_query(
                command, user_id, guild_id, listing_type, zone, subcategory,
                item, quantity, notes, scheduled_time, created_at, expires_at
            )
            
            if result:
                listing_id = result[0]['id']
                logger.info(f"Created listing {listing_id} for user {user_id}")
                return listing_id
            
        except Exception as e:
            logger.error(f"Error creating listing: {e}")
            raise
        
        return None
    
    async def get_zone_listings(self, guild_id: int, listing_type: str, zone: str) -> List[Dict[str, Any]]:
        """Get all active listings for a specific zone."""
        try:
            query = """
                SELECT l.*, u.username, u.reputation_avg, u.reputation_count
                FROM listings l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE l.guild_id = $1 
                  AND l.listing_type = $2 
                  AND l.zone = $3 
                  AND l.expires_at > $4
                  AND l.active = TRUE
                ORDER BY l.scheduled_time ASC
            """
            
            current_time = datetime.now(timezone.utc)
            return await self.execute_query(query, guild_id, listing_type, zone, current_time)
            
        except Exception as e:
            logger.error(f"Error getting zone listings: {e}")
            return []
    
    async def get_user_listings(self, user_id: int, guild_id: int, listing_type: str, zone: str) -> List[Dict[str, Any]]:
        """Get user's active listings for a specific zone."""
        try:
            query = """
                SELECT * FROM listings
                WHERE user_id = $1 
                  AND guild_id = $2 
                  AND listing_type = $3 
                  AND zone = $4 
                  AND expires_at > $5
                  AND active = TRUE
                ORDER BY created_at DESC
            """
            
            current_time = datetime.now(timezone.utc)
            return await self.execute_query(query, user_id, guild_id, listing_type, zone, current_time)
            
        except Exception as e:
            logger.error(f"Error getting user listings: {e}")
            return []
    
    async def remove_listing(self, listing_id: int, user_id: int) -> bool:
        """Remove a listing (soft delete)."""
        try:
            command = """
                UPDATE listings 
                SET active = FALSE, removed_at = $1
                WHERE id = $2 AND user_id = $3
            """
            
            result = await self.execute_command(command, datetime.now(timezone.utc), listing_id, user_id)
            return "UPDATE 1" in result
            
        except Exception as e:
            logger.error(f"Error removing listing: {e}")
            return False
    
    async def get_expired_listings(self) -> List[Dict[str, Any]]:
        """Get all expired listings."""
        try:
            query = """
                SELECT * FROM listings
                WHERE expires_at <= $1 
                  AND active = TRUE
                  AND reminded = FALSE
            """
            
            current_time = datetime.now(timezone.utc)
            return await self.execute_query(query, current_time)
            
        except Exception as e:
            logger.error(f"Error getting expired listings: {e}")
            return []
    
    async def mark_listing_reminded(self, listing_id: int):
        """Mark a listing as reminded about expiry."""
        try:
            command = """
                UPDATE listings 
                SET reminded = TRUE
                WHERE id = $1
            """
            await self.execute_command(command, listing_id)
            
        except Exception as e:
            logger.error(f"Error marking listing as reminded: {e}")
    
    async def add_reputation(self, rater_id: int, target_id: int, listing_id: int, rating: int, comment: str) -> bool:
        """Add a reputation rating."""
        try:
            # Check if already rated
            existing = await self.execute_query(
                "SELECT id FROM reputation WHERE rater_id = $1 AND target_id = $2 AND listing_id = $3",
                rater_id, target_id, listing_id
            )
            
            if existing:
                return False  # Already rated
            
            # Add reputation
            command = """
                INSERT INTO reputation (rater_id, target_id, listing_id, rating, comment, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """
            
            await self.execute_command(
                command, rater_id, target_id, listing_id, rating, comment, 
                datetime.now(timezone.utc)
            )
            
            # Update user reputation stats
            await self.update_user_reputation(target_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding reputation: {e}")
            return False
    
    async def update_user_reputation(self, user_id: int):
        """Update user's reputation statistics."""
        try:
            # Calculate new averages
            stats = await self.execute_query("""
                SELECT 
                    COUNT(*) as total_ratings,
                    AVG(rating) as avg_rating
                FROM reputation 
                WHERE target_id = $1
            """, user_id)
            
            if stats:
                total_ratings = stats[0]['total_ratings']
                avg_rating = float(stats[0]['avg_rating']) if stats[0]['avg_rating'] else 0.0
                
                # Update or insert user record
                command = """
                    INSERT INTO users (user_id, reputation_avg, reputation_count, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        reputation_avg = $2, 
                        reputation_count = $3, 
                        updated_at = $4
                """
                
                await self.execute_command(
                    command, user_id, avg_rating, total_ratings, 
                    datetime.now(timezone.utc)
                )
            
        except Exception as e:
            logger.error(f"Error updating user reputation: {e}")
    
    async def get_user_reputation(self, user_id: int) -> Dict[str, Any]:
        """Get user's reputation data."""
        try:
            query = """
                SELECT 
                    reputation_avg, 
                    reputation_count,
                    activity_score
                FROM users 
                WHERE user_id = $1
            """
            
            result = await self.execute_query(query, user_id)
            
            if result:
                return result[0]
            else:
                return {
                    'reputation_avg': 0.0,
                    'reputation_count': 0,
                    'activity_score': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting user reputation: {e}")
            return {
                'reputation_avg': 0.0,
                'reputation_count': 0,
                'activity_score': 0
            }
    
    async def ensure_user_exists(self, user_id: int):
        """Ensure a user exists in the users table."""
        try:
            command = """
                INSERT INTO users (user_id, created_at, updated_at)
                VALUES ($1, $2, $2)
                ON CONFLICT (user_id) DO NOTHING
            """
            await self.execute_command(command, user_id, datetime.now(timezone.utc))
            
        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
            raise

    async def cleanup_guild_data(self, guild_id: int):
        """Clean up data for a guild that the bot left."""
        try:
            # Deactivate all listings for the guild
            await self.execute_command(
                "UPDATE listings SET active = FALSE WHERE guild_id = $1",
                guild_id
            )
            
            # Remove guild config
            await self.execute_command(
                "DELETE FROM guild_configs WHERE guild_id = $1",
                guild_id
            )
            
            # Remove marketplace channels
            await self.execute_command(
                "DELETE FROM marketplace_channels WHERE guild_id = $1",
                guild_id
            )
            
            logger.info(f"Cleaned up data for guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up guild data: {e}")
