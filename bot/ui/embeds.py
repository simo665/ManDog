import discord
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MarketplaceEmbeds:
    """Creates Discord embeds for marketplace functionality."""

    COLORS = {
        'primary': 0x1E40AF,
        'secondary': 0x6B7280,
        'success': 0x10B981,
        'warning': 0xF59E0B,
        'error': 0xEF4444,
        'wts': 0xF59E0B,
        'wtb': 0x3B82F6,
        'neutral': 0x6B7280
    }

    def create_setup_embed(self) -> discord.Embed:
        """Create the setup embed for marketplace initialization."""
        embed = discord.Embed(
            title="🏗️ Marketplace Setup",
            description="Click the button below to set up marketplace channels for your server.",
            color=self.COLORS['primary']
        )

        embed.add_field(
            name="What happens when you set up?",
            value="• Creates WTS and WTB categories\n• Sets up channels for each zone\n• Configures persistent marketplace messages",
            inline=False
        )

        embed.set_footer(text="This will create channels and categories in your server")
        return embed

    def create_admin_embed(self) -> discord.Embed:
        """Create admin panel embed."""
        embed = discord.Embed(
            title="⚙️ Marketplace Admin Panel",
            description="Marketplace management options for administrators.",
            color=self.COLORS['secondary']
        )

        embed.add_field(
            name="Available Commands",
            value="• Setup marketplace channels\n• View marketplace statistics\n• Manage listings and users",
            inline=False
        )

        return embed

    def create_marketplace_embed(self, listing_type: str, zone: str, listings: List[Dict[str, Any]], page: int = 0) -> discord.Embed:
        """Create the main marketplace embed with queue information."""
        try:
            # Calculate pagination
            items_per_page = 10
            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            paginated_listings = listings[start_idx:end_idx]

            # Determine color and emoji
            color = self.COLORS['wts'] if listing_type.upper() == 'WTS' else self.COLORS['wtb']
            emoji = "🔸" if listing_type.upper() == 'WTS' else "🔹"

            # Count total items
            total_items = len(listings)

            # Create embed title
            title = f"{emoji} {listing_type.upper()} - {zone.title()}"

            embed = discord.Embed(
                title=title,
                description=f"📂 {zone.title()} ({total_items} item{'s' if total_items != 1 else ''})",
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            if not paginated_listings:
                embed.add_field(
                    name="No listings",
                    value=f"No active {listing_type} listings in {zone.title()}",
                    inline=False
                )
            else:
                # Group listings by user and display them with queue information
                for listing in paginated_listings:
                    user_id = listing['user_id']
                    item = listing['item']
                    scheduled_time = listing.get('scheduled_time')
                    notes = listing.get('notes', '')
                    listing_id = listing['id']

                    # Format the scheduled time using Discord timestamp
                    time_str = "Not scheduled"
                    if scheduled_time:
                        timestamp = int(scheduled_time.timestamp())
                        time_str = f"<t:{timestamp}:f> (<t:{timestamp}:R>)"

                    # Start building the listing display
                    listing_text = f"> 📦 **Item:**\n>  ╰┈➤ **{item}** by <@{user_id}>\n> ⏰ **Time:** {time_str}"

                    # Add queue information if it's a WTS listing
                    if listing_type.upper() == 'WTS':
                        # Get queue data for this listing (this would need to be passed from the calling function)
                        # For now, we'll assume it's available in the listing data
                        queues = listing.get('queues', {})
                        if queues and item in queues:
                            queue_users = queues[item]
                            if queue_users:
                                queue_mentions = ' • '.join([f"<@{user_id}>" for user_id in queue_users])
                                listing_text += f"\n> 👥 **Queue:** {queue_mentions}"

                    if notes:
                        listing_text += f"\n> 📝 **Notes:** {notes}"

                    embed.add_field(
                        name=f"📂 {zone.title()} (1 item)",
                        value=listing_text,
                        inline=False
                    )

            # Add pagination info if needed
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
            if total_pages > 1:
                embed.set_footer(text=f"Page {page + 1} of {total_pages}")

            return embed

        except Exception as e:
            logger.error(f"Error creating marketplace embed: {e}")
            # Return a basic error embed
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to load marketplace data",
                color=self.COLORS['error']
            )
            return embed

    def create_listing_confirmation_embed(self, listing_data: Dict[str, Any]) -> discord.Embed:
        """Create confirmation embed for new listing."""
        color = self.COLORS['wts'] if listing_data['listing_type'] == 'WTS' else self.COLORS['wtb']
        emoji = "🔸" if listing_data['listing_type'] == 'WTS' else "🔹"

        embed = discord.Embed(
            title=f"{emoji} Listing Created",
            description=f"Your {listing_data['listing_type']} listing has been created successfully!",
            color=color
        )

        embed.add_field(name="Zone", value=listing_data['zone'].title(), inline=True)
        embed.add_field(name="Item", value=listing_data['item'], inline=True)
        embed.add_field(name="Quantity", value=str(listing_data.get('quantity', 1)), inline=True)

        if listing_data.get('scheduled_time'):
            timestamp = int(listing_data['scheduled_time'].timestamp())
            embed.add_field(
                name="Scheduled Time", 
                value=f"<t:{timestamp}:f> (<t:{timestamp}:R>)", 
                inline=False
            )

        if listing_data.get('notes'):
            embed.add_field(name="Notes", value=listing_data['notes'], inline=False)

        embed.set_footer(text="Your listing will appear in the marketplace channel")
        return embed

    def create_queue_embed(self, zone: str, items: List[str]) -> discord.Embed:
        """Create embed for queue selection."""
        embed = discord.Embed(
            title="🔥 Join Queue",
            description=f"Select an item to queue for in {zone.title()}:",
            color=0xFF6B6B
        )

        if not items:
            embed.add_field(
                name="No Items Available",
                value=f"No items are currently listed for sale in {zone.title()}",
                inline=False
            )
        else:
            items_text = "\n".join([f"• {item}" for item in items[:10]])  # Show first 10
            if len(items) > 10:
                items_text += f"\n... and {len(items) - 10} more"

            embed.add_field(
                name="Available Items",
                value=items_text,
                inline=False
            )

        return embed

    def create_notification_embed(self, listing_data: Dict[str, Any], queue_users: List[int]) -> discord.Embed:
        """Create notification embed for scheduled trade time."""
        embed = discord.Embed(
            title="⏰ Trade Time Notification",
            description="It's time for your scheduled trade!",
            color=self.COLORS['warning']
        )

        embed.add_field(name="Item", value=listing_data['item'], inline=True)
        embed.add_field(name="Zone", value=listing_data['zone'].title(), inline=True)
        embed.add_field(name="Seller", value=f"<@{listing_data['user_id']}>", inline=True)

        if queue_users:
            queue_mentions = ', '.join([f"<@{user_id}>" for user_id in queue_users])
            embed.add_field(name="Queued Buyers", value=queue_mentions, inline=False)

        embed.set_footer(text="Please coordinate your trade in-game")
        return embed

    def create_rating_embed(self, listing_data: Dict[str, Any]) -> discord.Embed:
        """Create rating embed for post-trade feedback."""
        embed = discord.Embed(
            title="⭐ Rate Your Trade Experience",
            description="Please rate your trading experience with this seller:",
            color=self.COLORS['primary']
        )

        embed.add_field(name="Item", value=listing_data['item'], inline=True)
        embed.add_field(name="Zone", value=listing_data['zone'].title(), inline=True)
        embed.add_field(name="Seller", value=f"<@{listing_data['user_id']}>", inline=True)

        embed.add_field(
            name="Rating Scale",
            value="⭐ 1 - Poor\n⭐⭐ 2 - Fair\n⭐⭐⭐ 3 - Good\n⭐⭐⭐⭐ 4 - Very Good\n⭐⭐⭐⭐⭐ 5 - Excellent",
            inline=False
        )

        embed.set_footer(text="Your rating helps build trust in the community")
        return embed