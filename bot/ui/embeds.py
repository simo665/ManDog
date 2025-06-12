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
        """Create marketplace embed with pagination."""
        try:
            # Configuration
            items_per_page = 10
            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            page_listings = listings[start_idx:end_idx]

            # Color and emoji based on type
            color = self.COLORS['wts'] if listing_type.upper() == 'WTS' else self.COLORS['wtb']
            type_emoji = "🔸" if listing_type.upper() == 'WTS' else "🔹"

            # Create embed
            title = f"{type_emoji} {listing_type.upper()} - {zone.title()}"
            embed = discord.Embed(
                title=title,
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            if not page_listings:
                embed.description = f"No active {listing_type.upper()} listings in {zone.title()}"
                embed.add_field(
                    name="📝 How to List",
                    value=f"Use the **Add {listing_type.upper()}** button below to create a listing!",
                    inline=False
                )
            else:
                # Add listings
                for i, listing in enumerate(page_listings, start_idx + 1):
                    if listing_type.upper() == "WTS":
                        # New WTS format: 📂 [Monster] (X item)
                        field_name = f"📂 {listing['subcategory']} ({listing['quantity']} item)"

                        # Format timestamp
                        time_str = "No time set"
                        if listing.get('scheduled_time'):
                            timestamp = int(listing['scheduled_time'].timestamp())
                            time_str = f"<t:{timestamp}:f> (<t:{timestamp}:R>)"

                        # Format queue information
                        queue_str = "No queue"
                        if 'queues' in listing and listing['queues']:
                            queue_users = []
                            for item_name, users in listing['queues'].items():
                                for user_id in users:
                                    queue_users.append(f"<@{user_id}>")
                            if queue_users:
                                queue_str = " • ".join(queue_users)

                        # Notes
                        notes_str = listing.get('notes', '').strip() or "No notes."

                        # New WTS format
                        field_value = (
                            f"> 📦 Item: ╰┈➤ {listing['item']} by <@{listing['user_id']}>\n"
                            f"> ⏰ Time: {time_str}\n"
                            f"> 📝 Notes: {notes_str}\n"
                            f"> 👥 Queue: {queue_str}"
                        )
                    else:
                        # WTB format (unchanged)
                        # Format timestamp
                        time_str = "No time set"
                        if listing.get('scheduled_time'):
                            timestamp = int(listing['scheduled_time'].timestamp())
                            time_str = f"<t:{timestamp}:f> (<t:{timestamp}:R>)"

                        # Format reputation
                        rep_avg = listing.get('reputation_avg', 0.0)
                        if isinstance(rep_avg, str):
                            rep_avg = float(rep_avg) if rep_avg != 'None' else 0.0

                        stars = "⭐" * int(rep_avg) + "☆" * (5 - int(rep_avg))
                        reputation_str = f" {stars}" if rep_avg > 0 else ""

                        # Format field
                        field_name = f"{i}. {listing['subcategory']} ({listing['quantity']}x)"
                        field_value = (
                            f"**Item:** {listing['item']}\n"
                            f"**Buyer:** <@{listing['user_id']}>{reputation_str}\n"
                            f"**Time:** {time_str}"
                        )

                        if listing.get('notes'):
                            field_value += f"\n**Notes:** {listing['notes']}"

                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )

            # Add pagination info
            total_pages = max(1, (len(listings) + items_per_page - 1) // items_per_page)
            embed.set_footer(text=f"Page {page + 1}/{total_pages} • {len(listings)} total listings")

            return embed

        except Exception as e:
            logger.error(f"Error creating marketplace embed: {e}")
            return self.create_error_embed("Failed to create marketplace display")

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

    def create_setup_success_embed(self, channels_created: int) -> discord.Embed:
        """Create success embed for marketplace setup."""
        embed = discord.Embed(
            title="✅ Marketplace Setup Complete",
            description=f"Successfully created {channels_created} marketplace channels!",
            color=self.COLORS['success']
        )

        embed.add_field(
            name="What's Next?",
            value="• Use the marketplace channels to create WTS/WTB listings\n• Set your timezone with `/settimezone`\n• Start trading!",
            inline=False
        )

        embed.set_footer(text="Your marketplace is ready to use")
        return embed

    def create_error_embed(self, message: str) -> discord.Embed:
        """Create error embed."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=self.COLORS['error']
        )

        embed.set_footer(text="Please try again or contact an administrator")
        return embed