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

    async def execute_query(self, query: str, *params) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        async with self.pool.acquire() as connection:
            try:
                # Log queries that are related to matching
                if "listings" in query and ("listing_type" in query or "zone" in query):
                    logger.info(f"🗄️ DB DEBUG: Executing listing query")
                    logger.info(f"🗄️ DB DEBUG: Query: {query}")
                    logger.info(f"🗄️ DB DEBUG: Params: {params}")

                rows = await connection.fetch(query, *params)
                result = [dict(row) for row in rows]

                # Log results for matching queries
                if "listings" in query and ("listing_type" in query or "zone" in query):
                    logger.info(f"🗄️ DB DEBUG: Query returned {len(result)} rows")
                    for i, row in enumerate(result[:5]):  # Log first 5 rows
                        logger.info(f"🗄️ DB DEBUG: Row {i+1}: {row}")

                return result
            except Exception as e:
                logger.error(f"Database query error: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
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

            # Extract listing type
            if "wts" in channel_name or "🔸" in channel_name:
                listing_type = "WTS"
            elif "wtb" in channel_name or "🔹" in channel_name:
                listing_type = "WTB"
            else:
                listing_type = "UNKNOWN"

            # Extract zone from channel name - improved logic
            zone = "unknown"

            # Remove emoji and common prefixes to get the zone
            clean_name = channel_name
            for prefix in ["🔸", "🔹", "wts-", "wtb-"]:
                clean_name = clean_name.replace(prefix, "")

            # Remove common suffixes
            for suffix in ["-marketplace", "-market"]:
                clean_name = clean_name.replace(suffix, "")

            # Clean up and validate
            clean_name = clean_name.strip("-_ ")
            if clean_name and len(clean_name) > 1:
                zone = clean_name

            logger.info(f"Storing channel info: {channel.name} -> Type: {listing_type}, Zone: {zone}")

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
            result = await self.execute_command(command, message_id, guild_id, channel_id)

            # If no rows were updated, the channel info doesn't exist, so insert it
            if "UPDATE 0" in result:
                logger.warning(f"Channel {channel_id} not found in database, inserting...")
                insert_command = """
                    INSERT INTO marketplace_channels (guild_id, channel_id, message_id, listing_type, zone)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (channel_id) 
                    DO UPDATE SET message_id = $3, listing_type = $4, zone = $5
                """
                await self.execute_command(insert_command, guild_id, channel_id, message_id, listing_type, zone)

        except Exception as e:
            logger.error(f"Error storing marketplace message: {e}")
            raise

    async def get_guild_channels(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all marketplace channels for a guild."""
        try:
            query = """
                SELECT channel_id, listing_type, zone, message_id
                FROM marketplace_channels 
                WHERE guild_id = $1
            """
            return await self.execute_query(query, guild_id)

        except Exception as e:
            logger.error(f"Error getting guild channels: {e}")
            return []

    async def cleanup_invalid_channels(self, channel_ids: List[int]):
        """Remove database entries for channels that no longer exist."""
        try:
            if not channel_ids:
                return

            # Convert list to PostgreSQL array format
            placeholders = ','.join(f'${i+1}' for i in range(len(channel_ids)))

            command = f"""
                DELETE FROM marketplace_channels 
                WHERE channel_id = ANY(ARRAY[{placeholders}])
            """

            result = await self.execute_command(command, *channel_ids)
            logger.info(f"Cleaned up {len(channel_ids)} invalid channel entries: {result}")

        except Exception as e:
            logger.error(f"Error cleaning up invalid channels: {e}")
            raise

    async def cleanup_channel_data(self, channel_id: int):
        """Clean up data for a specific channel."""
        try:
            # Remove the channel from marketplace_channels
            await self.execute_command(
                "DELETE FROM marketplace_channels WHERE channel_id = $1",
                channel_id
            )

            logger.info(f"Cleaned up data for channel {channel_id}")

        except Exception as e:
            logger.error(f"Error cleaning up channel data: {e}")

    async def verify_channel_exists(self, guild_id: int, channel_id: int) -> bool:
        """Verify if a channel exists in the database."""
        try:
            result = await self.execute_query(
                "SELECT 1 FROM marketplace_channels WHERE guild_id = $1 AND channel_id = $2",
                guild_id, channel_id
            )
            return len(result) > 0

        except Exception as e:
            logger.error(f"Error verifying channel exists: {e}")
            return False

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
        """Get all active listings for a specific zone and type."""
        try:
            query = """
                SELECT l.*, u.username, u.reputation_avg
                FROM listings l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE l.guild_id = $1 
                  AND l.listing_type = $2 
                  AND l.zone = $3 
                  AND l.active = TRUE 
                  AND l.expires_at > $4
                ORDER BY l.scheduled_time ASC, l.created_at DESC
            """

            current_time = datetime.now(timezone.utc)
            results = await self.execute_query(query, guild_id, listing_type, zone, current_time)

            # Additional validation to ensure no cross-contamination
            filtered_results = []
            for listing in results:
                if listing['listing_type'] == listing_type and listing['zone'] == zone:
                    filtered_results.append(listing)
                else:
                    logger.warning(f"Filtered out mismatched listing: {listing['id']} - expected {listing_type}/{zone}, got {listing['listing_type']}/{listing['zone']}")

            return filtered_results

        except Exception as e:
            logger.error(f"Error getting zone listings: {e}")
            return []

    async def get_listing_queues(self, listing_id: int) -> Dict[str, List[int]]:
        """Get queued items and buyers for a specific listing (for WTS All Items)."""
        try:
            queue_data = await self.execute_query(
                """
                SELECT q.user_id, q.requested_item
                FROM queues q
                WHERE q.listing_id = $1 AND q.queue_type = 'buyer_queue'
                ORDER BY q.created_at ASC
                """,
                listing_id
            )

            # Group by requested item
            queued_items = {}
            for queue_entry in queue_data or []:
                item = queue_entry['requested_item']
                user_id = queue_entry['user_id']

                if item not in queued_items:
                    queued_items[item] = []
                queued_items[item].append(user_id)

            return queued_items
        except Exception as e:
            logger.error(f"Error getting listing queues: {e}")
            return {}

    async def add_to_queue(self, user_id: int, listing_id: int, requested_item: str) -> bool:
        """Add a buyer to queue for a specific item under WTS All Items listing."""
        try:
            await self.execute_command(
                """
                INSERT INTO queues (user_id, listing_id, queue_type, requested_item, created_at)
                VALUES ($1, $2, 'buyer_queue', $3, $4)
                ON CONFLICT (user_id, listing_id) 
                DO UPDATE SET requested_item = $3, created_at = $4
                """,
                user_id, listing_id, requested_item, datetime.now(timezone.utc)
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return False

    async def remove_from_queue(self, user_id: int, listing_id: int) -> bool:
        """Remove a buyer from queue for a listing."""
        try:
            await self.execute_command(
                """
                DELETE FROM queues 
                WHERE user_id = $1 AND listing_id = $2 AND queue_type = 'buyer_queue'
                """,
                user_id, listing_id
            )
            return True
        except Exception as e:
            logger.error(f"Error removing from queue: {e}")
            return False

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

    async def add_to_queue(self, listing_id: int, user_id: int, item_name: str) -> bool:
        """Add a user to the queue for a specific item."""
        try:
            await self.execute_command(
                """
                INSERT INTO listing_queues (listing_id, user_id, item_name, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (listing_id, user_id, item_name) DO NOTHING
                """,
                listing_id, user_id, item_name, datetime.now(timezone.utc)
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return False

    async def get_listing_queues(self, listing_id: int) -> Dict[str, List[int]]:
        """Get all queued items and buyers for a listing."""
        try:
            results = await self.execute_query(
                """
                SELECT item_name, user_id 
                FROM listing_queues 
                WHERE listing_id = $1
                ORDER BY item_name, created_at ASC
                """,
                listing_id
            )

            queues = {}
            for row in results:
                item_name = row['item_name']
                user_id = row['user_id']

                if item_name not in queues:
                    queues[item_name] = []
                queues[item_name].append(user_id)

            return queues
        except Exception as e:
            logger.error(f"Error getting listing queues: {e}")
            return {}

    async def cleanup_guild_data(self, guild_id: int):
        """Clean up all data for a guild."""
        try:
            await self.execute_command(
                "DELETE FROM listings WHERE guild_id = $1",
                guild_id
            )
            await self.execute_command(
                "DELETE FROM marketplace_channels WHERE guild_id = $1", 
                guild_id
            )
            logger.info(f"Cleaned up data for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error cleaning up guild data: {e}")