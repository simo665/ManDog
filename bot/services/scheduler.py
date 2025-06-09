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
