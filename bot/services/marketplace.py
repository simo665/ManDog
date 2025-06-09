"""
Core marketplace business logic and services.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from bot.ui.embeds import MarketplaceEmbeds

logger = logging.getLogger(__name__)

class MarketplaceService:
    """Core service for marketplace operations."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = MarketplaceEmbeds()
    
    async def refresh_marketplace_embed(self, guild_id: int, channel_id: int):
        """Refresh the marketplace embed in a specific channel."""
        try:
            # Get channel info
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT * FROM marketplace_channels WHERE guild_id = $1 AND channel_id = $2",
                guild_id, channel_id
            )
            
            if not channel_info:
                logger.warning(f"No channel info found for {channel_id}")
                return
            
            channel_data = channel_info[0]
            listing_type = channel_data['listing_type']
            zone = channel_data['zone']
            message_id = channel_data['message_id']
            
            # Get active listings for this zone
            listings = await self.bot.db_manager.get_zone_listings(guild_id, listing_type, zone)
            
            # Create updated embed
            embed = self.embeds.create_marketplace_embed(listing_type, zone, listings)
            
            # Get channel and message
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel {channel_id}")
                return
            
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    logger.info(f"Updated marketplace embed in {channel.name}")
                except:
                    # Message not found, send new one
                    await self.send_new_marketplace_embed(channel, listing_type, zone)
            else:
                # No message ID stored, send new one
                await self.send_new_marketplace_embed(channel, listing_type, zone)
                
        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")
    
    async def send_new_marketplace_embed(self, channel, listing_type: str, zone: str):
        """Send a new marketplace embed to a channel."""
        try:
            from bot.ui.views import MarketplaceView
            
            # Get listings for this zone
            listings = await self.bot.db_manager.get_zone_listings(
                channel.guild.id, listing_type, zone
            )
            
            # Create embed and view
            embed = self.embeds.create_marketplace_embed(listing_type, zone, listings)
            view = MarketplaceView(self.bot, listing_type, zone)
            
            # Send message
            message = await channel.send(embed=embed, view=view)
            
            # Store message ID
            await self.bot.db_manager.store_marketplace_message(
                channel.guild.id, channel.id, message.id, listing_type, zone
            )
            
            logger.info(f"Sent new marketplace embed to {channel.name}")
            
        except Exception as e:
            logger.error(f"Error sending new marketplace embed: {e}")
    
    async def create_listing(self, user_id: int, guild_id: int, listing_data: Dict[str, Any]) -> Optional[int]:
        """Create a new marketplace listing."""
        try:
            # Validate listing data
            required_fields = ['listing_type', 'zone', 'subcategory', 'item', 'scheduled_time']
            for field in required_fields:
                if field not in listing_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Set defaults
            quantity = listing_data.get('quantity', 1)
            notes = listing_data.get('notes', '')
            
            # Create listing in database
            listing_id = await self.bot.db_manager.create_listing(
                user_id=user_id,
                guild_id=guild_id,
                listing_type=listing_data['listing_type'],
                zone=listing_data['zone'],
                subcategory=listing_data['subcategory'],
                item=listing_data['item'],
                quantity=quantity,
                notes=notes,
                scheduled_time=listing_data['scheduled_time']
            )
            
            if listing_id:
                # Refresh relevant marketplace embeds
                await self.refresh_marketplace_embeds_for_zone(
                    guild_id, listing_data['listing_type'], listing_data['zone']
                )
                
                # Update user activity score
                await self.update_user_activity(user_id, 'listing_created')
                
                logger.info(f"Created listing {listing_id} for user {user_id}")
                return listing_id
            
        except Exception as e:
            logger.error(f"Error creating listing: {e}")
            raise
        
        return None
    
    async def refresh_marketplace_embeds_for_zone(self, guild_id: int, listing_type: str, zone: str):
        """Refresh all marketplace embeds for a specific zone."""
        try:
            # Get channel for this listing type and zone
            channels = await self.bot.db_manager.execute_query(
                "SELECT channel_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = $2 AND zone = $3",
                guild_id, listing_type, zone
            )
            
            for channel_data in channels:
                await self.refresh_marketplace_embed(guild_id, channel_data['channel_id'])
                
        except Exception as e:
            logger.error(f"Error refreshing marketplace embeds for zone: {e}")
    
    async def remove_listing(self, listing_id: int, user_id: int) -> bool:
        """Remove a marketplace listing."""
        try:
            # Get listing info before removal
            listing_info = await self.bot.db_manager.execute_query(
                "SELECT guild_id, listing_type, zone FROM listings WHERE id = $1 AND user_id = $2",
                listing_id, user_id
            )
            
            if not listing_info:
                return False
            
            # Remove listing
            success = await self.bot.db_manager.remove_listing(listing_id, user_id)
            
            if success:
                listing_data = listing_info[0]
                
                # Refresh marketplace embeds
                await self.refresh_marketplace_embeds_for_zone(
                    listing_data['guild_id'], 
                    listing_data['listing_type'], 
                    listing_data['zone']
                )
                
                logger.info(f"Removed listing {listing_id} for user {user_id}")
                return True
            
        except Exception as e:
            logger.error(f"Error removing listing: {e}")
        
        return False
    
    async def update_user_activity(self, user_id: int, activity_type: str):
        """Update user activity score."""
        try:
            # Activity score points
            activity_points = {
                'listing_created': 5,
                'listing_completed': 10,
                'rating_given': 2,
                'rating_received': 3
            }
            
            points = activity_points.get(activity_type, 1)
            
            # Update user activity score
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO users (user_id, activity_score, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    activity_score = users.activity_score + $2,
                    updated_at = $3
                """,
                user_id, points, datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
    
    async def get_matching_listings(self, listing_type: str, zone: str, item: str, guild_id: int) -> List[Dict[str, Any]]:
        """Get matching listings for queue system."""
        try:
            # Find opposite type listings
            opposite_type = "WTB" if listing_type == "WTS" else "WTS"
            
            query = """
                SELECT l.*, u.username, u.reputation_avg
                FROM listings l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE l.guild_id = $1 
                  AND l.listing_type = $2 
                  AND l.zone = $3 
                  AND (l.item = $4 OR l.item = 'All Items')
                  AND l.expires_at > $5
                  AND l.active = TRUE
                ORDER BY l.scheduled_time ASC
            """
            
            current_time = datetime.now(timezone.utc)
            return await self.bot.db_manager.execute_query(
                query, guild_id, opposite_type, zone, item, current_time
            )
            
        except Exception as e:
            logger.error(f"Error getting matching listings: {e}")
            return []
    
    async def add_to_queue(self, user_id: int, listing_id: int, queue_type: str) -> bool:
        """Add user to a listing queue."""
        try:
            command = """
                INSERT INTO queues (user_id, listing_id, queue_type, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, listing_id) DO NOTHING
            """
            
            result = await self.bot.db_manager.execute_command(
                command, user_id, listing_id, queue_type, datetime.now(timezone.utc)
            )
            
            return "INSERT" in result
            
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return False
    
    async def notify_queue_matches(self, listing_id: int):
        """Notify users in queue about matching listings."""
        try:
            # Get users in queue for this listing
            queue_users = await self.bot.db_manager.execute_query(
                "SELECT user_id FROM queues WHERE listing_id = $1 AND notified = FALSE",
                listing_id
            )
            
            # Get listing details
            listing_details = await self.bot.db_manager.execute_query(
                "SELECT * FROM listings WHERE id = $1",
                listing_id
            )
            
            if not listing_details:
                return
            
            listing = listing_details[0]
            
            # Send DM notifications
            for queue_user in queue_users:
                try:
                    user = self.bot.get_user(queue_user['user_id'])
                    if user:
                        embed = self.embeds.create_queue_notification_embed(listing)
                        await user.send(embed=embed)
                        
                        # Mark as notified
                        await self.bot.db_manager.execute_command(
                            "UPDATE queues SET notified = TRUE WHERE user_id = $1 AND listing_id = $2",
                            queue_user['user_id'], listing_id
                        )
                        
                except Exception as e:
                    logger.error(f"Error sending queue notification to user {queue_user['user_id']}: {e}")
            
        except Exception as e:
            logger.error(f"Error notifying queue matches: {e}")
    
    async def get_user_statistics(self, user_id: int, guild_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        try:
            # Get basic user data
            user_data = await self.bot.db_manager.get_user_reputation(user_id)
            
            # Get listing statistics
            listing_stats = await self.bot.db_manager.execute_query(
                """
                SELECT 
                    COUNT(*) as total_listings,
                    COUNT(*) FILTER (WHERE listing_type = 'WTS') as wts_count,
                    COUNT(*) FILTER (WHERE listing_type = 'WTB') as wtb_count,
                    COUNT(*) FILTER (WHERE active = TRUE) as active_listings
                FROM listings 
                WHERE user_id = $1 AND guild_id = $2
                """,
                user_id, guild_id
            )
            
            # Get transaction statistics
            transaction_stats = await self.bot.db_manager.execute_query(
                """
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_transactions
                FROM transactions 
                WHERE (seller_id = $1 OR buyer_id = $1)
                """,
                user_id
            )
            
            # Combine all statistics
            stats = {
                **user_data,
                'total_listings': listing_stats[0]['total_listings'] if listing_stats else 0,
                'wts_count': listing_stats[0]['wts_count'] if listing_stats else 0,
                'wtb_count': listing_stats[0]['wtb_count'] if listing_stats else 0,
                'active_listings': listing_stats[0]['active_listings'] if listing_stats else 0,
                'total_transactions': transaction_stats[0]['total_transactions'] if transaction_stats else 0,
                'completed_transactions': transaction_stats[0]['completed_transactions'] if transaction_stats else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
