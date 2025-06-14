"""
Scheduler service for handling timed events like listing expiry and reminders.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from bot.ui.embeds import MarketplaceEmbeds

logger = logging.getLogger(__name__)

class ExpiryScheduler:
    """Handles scheduled tasks for listing expiry and reminders."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = MarketplaceEmbeds()
    
    async def check_expired_listings(self):
        """Check for expired listings and send reminders."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check for listings expiring in 24 hours (reminder)
            await self.send_expiry_reminders(current_time)
            
            # Check for already expired listings
            await self.handle_expired_listings(current_time)
            
        except Exception as e:
            logger.error(f"Error in expiry check: {e}")
    
    async def send_expiry_reminders(self, current_time: datetime):
        """Send reminders for listings expiring soon."""
        try:
            # Get listings expiring in 24 hours
            reminder_time = current_time + timedelta(hours=24)
            
            listings_to_remind = await self.bot.db_manager.execute_query(
                """
                SELECT l.*, u.username
                FROM listings l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE l.expires_at BETWEEN $1 AND $2
                  AND l.active = TRUE
                  AND l.reminded = FALSE
                """,
                current_time, reminder_time
            )
            
            for listing in listings_to_remind:
                await self.send_expiry_reminder(listing)
                await self.bot.db_manager.mark_listing_reminded(listing['id'])
            
            if listings_to_remind:
                logger.info(f"Sent {len(listings_to_remind)} expiry reminders")
            
        except Exception as e:
            logger.error(f"Error sending expiry reminders: {e}")
    
    async def send_expiry_reminder(self, listing: Dict[str, Any]):
        """Send expiry reminder to a user."""
        try:
            user = self.bot.get_user(listing['user_id'])
            if not user:
                return
            
            # Create reminder embed
            embed = self.create_expiry_reminder_embed(listing)
            
            # Create extend button view
            view = ExtendListingView(self.bot, listing['id'])
            
            await user.send(embed=embed, view=view)
            
            logger.info(f"Sent expiry reminder for listing {listing['id']} to user {listing['user_id']}")
            
        except Exception as e:
            logger.error(f"Error sending expiry reminder for listing {listing['id']}: {e}")
    
    def create_expiry_reminder_embed(self, listing: Dict[str, Any]) -> "discord.Embed":
        """Create expiry reminder embed."""
        import discord
        
        embed = discord.Embed(
            title="⏰ Listing Expiring Soon!",
            description=(
                f"Your **{listing['listing_type']}** listing for **{listing['item']}** "
                f"in **{listing['zone'].title()}** will expire in less than 24 hours."
            ),
            color=self.embeds.COLORS['warning'],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="📂 Details",
            value=(
                f"**Zone:** {listing['zone'].title()}\n"
                f"**Category:** {listing['subcategory']}\n"
                f"**Item:** {listing['item']}\n"
                f"**Quantity:** {listing['quantity']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⏰ Expires",
            value=f"<t:{int(listing['expires_at'].timestamp())}:R>",
            inline=True
        )
        
        if listing['notes']:
            embed.add_field(
                name="📝 Notes",
                value=listing['notes'][:200] + ("..." if len(listing['notes']) > 200 else ""),
                inline=False
            )
        
        embed.set_footer(text="Use the button below to extend this listing")
        
        return embed
    
    async def handle_expired_listings(self, current_time: datetime):
        """Handle listings that have already expired."""
        try:
            # Get expired listings
            expired_listings = await self.bot.db_manager.execute_query(
                """
                SELECT l.*, u.username
                FROM listings l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE l.expires_at <= $1
                  AND l.active = TRUE
                """,
                current_time
            )
            
            for listing in expired_listings:
                await self.expire_listing(listing)
            
            if expired_listings:
                logger.info(f"Expired {len(expired_listings)} listings")
            
        except Exception as e:
            logger.error(f"Error handling expired listings: {e}")
    
    async def expire_listing(self, listing: Dict[str, Any]):
        """Expire a single listing."""
        try:
            # Mark listing as inactive
            await self.bot.db_manager.execute_command(
                "UPDATE listings SET active = FALSE WHERE id = $1",
                listing['id']
            )
            
            # Send expiry notification to user
            user = self.bot.get_user(listing['user_id'])
            if user:
                embed = self.create_expiry_notification_embed(listing)
                await user.send(embed=embed)
            
            # Refresh marketplace embeds
            from bot.services.marketplace import MarketplaceService
            marketplace_service = MarketplaceService(self.bot)
            await marketplace_service.refresh_marketplace_embeds_for_zone(
                listing['guild_id'], listing['listing_type'], listing['zone']
            )
            
            logger.info(f"Expired listing {listing['id']}")
            
        except Exception as e:
            logger.error(f"Error expiring listing {listing['id']}: {e}")
    
    def create_expiry_notification_embed(self, listing: Dict[str, Any]) -> "discord.Embed":
        """Create expiry notification embed."""
        import discord
        
        embed = discord.Embed(
            title="📋 Listing Expired",
            description=(
                f"Your **{listing['listing_type']}** listing for **{listing['item']}** "
                f"in **{listing['zone'].title()}** has expired and been removed from the marketplace."
            ),
            color=self.embeds.COLORS['error'],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="📂 Details",
            value=(
                f"**Zone:** {listing['zone'].title()}\n"
                f"**Category:** {listing['subcategory']}\n"
                f"**Item:** {listing['item']}\n"
                f"**Quantity:** {listing['quantity']}"
            ),
            inline=False
        )
        
        embed.set_footer(text="You can create a new listing anytime using the marketplace channels")
        
        return embed
    
    async def extend_listing(self, listing_id: int, user_id: int, days: int = 14) -> bool:
        """Extend a listing's expiry date."""
        try:
            # Verify user owns the listing
            listing = await self.bot.db_manager.execute_query(
                "SELECT * FROM listings WHERE id = $1 AND user_id = $2 AND active = TRUE",
                listing_id, user_id
            )
            
            if not listing:
                return False
            
            listing_data = listing[0]
            
            # Calculate new expiry date
            current_expiry = listing_data['expires_at']
            new_expiry = current_expiry + timedelta(days=days)
            
            # Update listing
            await self.bot.db_manager.execute_command(
                "UPDATE listings SET expires_at = $1, reminded = FALSE WHERE id = $2",
                new_expiry, listing_id
            )
            
            logger.info(f"Extended listing {listing_id} by {days} days")
            return True
            
        except Exception as e:
            logger.error(f"Error extending listing {listing_id}: {e}")
            return False
    
    async def schedule_listing_activation(self, listing_id: int, activation_time: datetime):
        """Schedule a listing to become active at a specific time."""
        try:
            current_time = datetime.now(timezone.utc)
            
            if activation_time <= current_time:
                # Activate immediately
                await self.activate_listing(listing_id)
            else:
                # Schedule for later (this would need a more sophisticated scheduler)
                delay = (activation_time - current_time).total_seconds()
                
                # For now, we'll store the scheduled time and check it in our regular checks
                await self.bot.db_manager.execute_command(
                    "UPDATE listings SET scheduled_time = $1 WHERE id = $2",
                    activation_time, listing_id
                )
            
        except Exception as e:
            logger.error(f"Error scheduling listing activation: {e}")
    
    async def activate_listing(self, listing_id: int):
        """Activate a scheduled listing."""
        try:
            # Mark listing as active
            await self.bot.db_manager.execute_command(
                "UPDATE listings SET active = TRUE WHERE id = $1",
                listing_id
            )
            
            # Get listing details for refresh
            listing = await self.bot.db_manager.execute_query(
                "SELECT guild_id, listing_type, zone FROM listings WHERE id = $1",
                listing_id
            )
            
            if listing:
                listing_data = listing[0]
                
                # Refresh marketplace embeds
                from bot.services.marketplace import MarketplaceService
                marketplace_service = MarketplaceService(self.bot)
                await marketplace_service.refresh_marketplace_embeds_for_zone(
                    listing_data['guild_id'], 
                    listing_data['listing_type'], 
                    listing_data['zone']
                )
            
            logger.info(f"Activated listing {listing_id}")
            
        except Exception as e:
            logger.error(f"Error activating listing: {e}")

class ExtendListingView:
    """View for extending listing expiry."""
    
    def __init__(self, bot, listing_id: int):
        self.bot = bot
        self.listing_id = listing_id
    
    # This would implement the Discord UI for extending listings
    # For now, we'll keep it as a placeholder class
    pass
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
import discord

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for handling scheduled events and notifications."""

    def __init__(self, bot):
        self.bot = bot
        self.running = False

    async def start(self):
        """Start the scheduler service."""
        self.running = True
        asyncio.create_task(self.event_loop())
        logger.info("Scheduler service started")

    async def stop(self):
        """Stop the scheduler service."""
        self.running = False
        logger.info("Scheduler service stopped")

    async def event_loop(self):
        """Main event loop for checking scheduled events."""
        while self.running:
            try:
                await self.check_pending_events()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler event loop: {e}")
                await asyncio.sleep(60)

    async def check_pending_events(self):
        """Check for events that should trigger."""
        try:
            pending_events = await self.bot.db_manager.get_pending_events()
            
            for event in pending_events:
                await self.trigger_event(event)

        except Exception as e:
            logger.error(f"Error checking pending events: {e}")

    async def trigger_event(self, event: Dict[str, Any]):
        """Trigger a scheduled event."""
        try:
            listing_id = event['listing_id']
            guild_id = event['guild_id']
            seller_id = event['user_id']
            item_name = event['item']
            zone = event['zone']

            # Mark event as started
            await self.bot.db_manager.execute_command(
                "UPDATE scheduled_events SET status = 'started' WHERE id = $1",
                event['id']
            )

            # Deactivate the listing
            await self.bot.db_manager.execute_command(
                "UPDATE listings SET active = FALSE WHERE id = $1",
                listing_id
            )

            # Get guild and create notification
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.warning(f"Guild {guild_id} not found for event")
                return

            # Get queue participants
            queue_data = await self.bot.db_manager.get_listing_queues(listing_id)
            participants = []
            for item_queues in queue_data.values():
                participants.extend(item_queues)

            # First, remove the item from the seller's listing and refresh embed
            await self.remove_item_from_listing(listing_id, item_name, guild_id, zone)

            # Create notification embed
            embed = discord.Embed(
                title="⏳ Event Started",
                description=f"The event for **{item_name}** in **{zone.title()}** has started!\n\nPlease confirm your participation.",
                color=0xFFAA00,
                timestamp=datetime.now(timezone.utc)
            )

            # Create confirmation view for each participant
            from bot.ui.views_ordering import EventConfirmationView
            
            # Send notification to seller
            try:
                seller = guild.get_member(seller_id)
                if seller:
                    seller_view = EventConfirmationView(self.bot, event['id'], "seller", seller_id)
                    await seller.send(embed=embed, view=seller_view)
                    logger.info(f"Sent event notification to seller {seller_id}")
            except discord.Forbidden:
                logger.warning(f"Could not DM seller {seller_id}")

            # Send notifications to queue participants
            for participant_id in participants:
                try:
                    participant = guild.get_member(participant_id)
                    if participant:
                        participant_view = EventConfirmationView(self.bot, event['id'], "buyer", participant_id)
                        await participant.send(embed=embed, view=participant_view)
                        logger.info(f"Sent event notification to participant {participant_id}")
                except discord.Forbidden:
                    logger.warning(f"Could not DM participant {participant_id}")

            logger.info(f"Triggered event {event['id']} for listing {listing_id}")

        except Exception as e:
            logger.error(f"Error triggering event {event['id']}: {e}")

    async def remove_item_from_listing(self, listing_id: int, item_name: str, guild_id: int, zone: str):
        """Remove item from listing and refresh marketplace embed."""
        try:
            # Get listing info first
            listing_info = await self.bot.db_manager.execute_query(
                "SELECT listing_type, zone FROM listings WHERE id = $1",
                listing_id
            )
            
            if not listing_info:
                logger.warning(f"Listing {listing_id} not found")
                return
                
            listing_data = listing_info[0]
            listing_type = listing_data['listing_type']
            
            # Mark listing as inactive (remove from marketplace)
            await self.bot.db_manager.execute_command(
                "UPDATE listings SET active = FALSE WHERE id = $1",
                listing_id
            )
            
            # Refresh marketplace embeds to show the item is removed
            from bot.services.marketplace import MarketplaceService
            marketplace_service = MarketplaceService(self.bot)
            await marketplace_service.refresh_marketplace_embeds_for_zone(
                guild_id, listing_type, zone
            )
            
            logger.info(f"Removed listing {listing_id} for item {item_name} and refreshed embeds")
            
        except Exception as e:
            logger.error(f"Error removing item from listing: {e}")

    async def schedule_rating_prompt(self, event_id: int, delay_seconds: int = 10):
        """Schedule rating prompt after delay."""
        try:
            await asyncio.sleep(10)
            
            # Get event details
            event_data = await self.bot.db_manager.execute_query(
                """
                SELECT se.*, l.user_id as seller_id, l.item, l.zone, l.guild_id
                FROM scheduled_events se
                JOIN listings l ON se.listing_id = l.id
                WHERE se.id = $1
                """,
                event_id
            )

            if not event_data:
                logger.warning(f"No event data found for event_id {event_id}")
                return

            event = event_data[0]
            
            # Get confirmed participants from database
            confirmed_participants = await self.bot.db_manager.execute_query(
                """
                SELECT user_id FROM event_confirmations 
                WHERE event_id = $1 AND confirmed = TRUE AND role = 'buyer'
                """,
                event_id
            )

            if not confirmed_participants:
                logger.info(f"No confirmed participants found for event {event_id}")
                return

            # Send rating prompts to confirmed buyers only
            from bot.ui.views_ordering import EventRatingView
            
            logger.info(f"Sending rating prompts to {len(confirmed_participants)} confirmed participants")
            
            for participant_data in confirmed_participants:
                participant_id = participant_data['user_id']
                try:
                    guild = self.bot.get_guild(event['guild_id'])
                    if guild:
                        participant = guild.get_member(participant_id)
                        if participant:
                            view = EventRatingView(self.bot, event_id, event['seller_id'])
                            
                            embed = discord.Embed(
                                title="⭐ Rate Your Experience",
                                description=f"Please rate your experience with the **{event['item']}** event in **{event['zone'].title()}**",
                                color=0x3B82F6,
                                timestamp=datetime.now(timezone.utc)
                            )
                            
                            embed.add_field(
                                name="Seller",
                                value=f"<@{event['seller_id']}>",
                                inline=True
                            )
                            
                            embed.add_field(
                                name="Item",
                                value=event['item'],
                                inline=True
                            )
                            
                            embed.add_field(
                                name="Zone",
                                value=event['zone'].title(),
                                inline=True
                            )
                            
                            embed.set_footer(text="Your rating helps the community!")
                            
                            await participant.send(embed=embed, view=view)
                            logger.info(f"Sent rating prompt to participant {participant_id}")
                        else:
                            logger.warning(f"Could not find member {participant_id} in guild")
                    else:
                        logger.warning(f"Could not find guild {event['guild_id']}")
                except Exception as e:
                    logger.error(f"Error sending rating prompt to {participant_id}: {e}")

        except Exception as e:
            logger.error(f"Error in rating prompt schedule: {e}")

    async def check_ratings_complete_and_send_summary(self, event_id: int):
        """Check if all ratings are complete and send summary to mods channel."""
        try:
            # Get event and confirmed participants
            event_data = await self.bot.db_manager.execute_query(
                """
                SELECT se.*, l.user_id as seller_id, l.item, l.zone, l.guild_id
                FROM scheduled_events se
                JOIN listings l ON se.listing_id = l.id
                WHERE se.id = $1
                """,
                event_id
            )

            if not event_data:
                return

            event = event_data[0]
            
            # Get confirmed participants
            confirmed_participants = await self.bot.db_manager.execute_query(
                """
                SELECT user_id FROM event_confirmations 
                WHERE event_id = $1 AND confirmed = TRUE AND role = 'buyer'
                """,
                event_id
            )

            # Get submitted ratings
            submitted_ratings = await self.bot.db_manager.execute_query(
                """
                SELECT rater_id, rating, comment, created_at 
                FROM event_ratings 
                WHERE event_id = $1
                """,
                event_id
            )

            confirmed_count = len(confirmed_participants)
            ratings_count = len(submitted_ratings)

            # Check if all ratings are submitted
            if ratings_count >= confirmed_count and confirmed_count > 0:
                await self.send_rating_summary(event, submitted_ratings)

        except Exception as e:
            logger.error(f"Error checking ratings completion: {e}")

    async def send_rating_summary(self, event: dict, ratings: list):
        """Send rating summary to mods channel."""
        try:
            guild_id = event['guild_id']
            
            # Get the logs/rates channel
            channel_data = await self.bot.db_manager.execute_query(
                """
                SELECT admin_channel_id FROM guild_rating_configs 
                WHERE guild_id = $1
                """,
                guild_id
            )

            if not channel_data or not channel_data[0]['admin_channel_id']:
                logger.info(f"No mods channel configured for guild {guild_id}, skipping summary")
                return

            channel_id = channel_data[0]['admin_channel_id']
            guild = self.bot.get_guild(guild_id)
            
            if not guild:
                logger.warning(f"Could not find guild {guild_id}")
                return

            channel = guild.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel {channel_id}")
                return

            # Calculate average rating
            total_rating = sum(r['rating'] for r in ratings)
            avg_rating = total_rating / len(ratings) if ratings else 0
            
            # Create summary embed
            embed = discord.Embed(
                title="📊 Trade Rating Summary",
                description=f"Event ratings have been collected for **{event['item']}** in **{event['zone'].title()}**",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="🛒 Seller",
                value=f"<@{event['seller_id']}>",
                inline=True
            )

            embed.add_field(
                name="⭐ Average Rating",
                value=f"{avg_rating:.1f}/5 ({'⭐' * int(avg_rating)})",
                inline=True
            )

            embed.add_field(
                name="📊 Total Ratings",
                value=str(len(ratings)),
                inline=True
            )

            # Add buyer ratings
            buyers_text = ""
            for rating_data in ratings:
                rating_stars = "⭐" * rating_data['rating']
                buyers_text += f"<@{rating_data['rater_id']}>: {rating_stars} ({rating_data['rating']}/5)\n"
                if rating_data['comment']:
                    buyers_text += f"💬 *{rating_data['comment'][:100]}{'...' if len(rating_data['comment']) > 100 else ''}*\n"
                buyers_text += "\n"

            if buyers_text:
                embed.add_field(
                    name="🛍️ Buyer Ratings",
                    value=buyers_text[:1024],
                    inline=False
                )

            embed.set_footer(text="Event rating summary")

            await channel.send(embed=embed)
            logger.info(f"Sent rating summary to channel {channel_id}")

        except Exception as e:
            logger.error(f"Error sending rating summary: {e}")
