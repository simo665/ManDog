"""
Embed creation utilities for the marketplace bot.
"""

import discord
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MarketplaceEmbeds:
    """Utility class for creating Discord embeds."""

    # FFXI-themed colors
    COLORS = {
        'primary': 0x1E40AF,      # Blue
        'success': 0x059669,      # Green
        'warning': 0xD97706,      # Orange
        'error': 0xDC2626,        # Red
        'info': 0x7C3AED,         # Purple
        'wts': 0xF59E0B,          # Amber for WTS
        'wtb': 0x3B82F6           # Blue for WTB
    }

    def create_setup_embed(self) -> discord.Embed:
        """Create the initial setup embed."""
        embed = discord.Embed(
            title="🏪 Mandok Marketplace Setup",
            description=(
                "Welcome to the Mandok marketplace system for Final Fantasy XI!\n\n"
                "This bot will help you manage player-driven trading with:\n"
                "• **WTS/WTB Categories** - Organized by content zones\n"
                "• **Interactive Listings** - UI-driven with buttons and dropdowns\n"
                "• **Reputation System** - Build trust in the community\n"
                "• **Auto-Expiry** - Keep listings fresh and relevant\n\n"
                "Click the button below to set up the marketplace channels."
            ),
            color=self.COLORS['primary'],
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📋 What will be created:",
            value=(
                "• **WTS - Sellers** category with 5 channels\n"
                "• **WTB - Buyers** category with 5 channels\n"
                "• Channels: Sky, Sea, Dynamis, Limbus, Others\n"
                "• Interactive embeds in each channel"
            ),
            inline=False
        )

        embed.set_footer(text="Mandok Marketplace Bot", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
        return embed

    def create_admin_embed(self) -> discord.Embed:
        """Create admin control panel embed."""
        embed = discord.Embed(
            title="⚙️ Marketplace Administration",
            description="Administrative controls for the marketplace system.",
            color=self.COLORS['info'],
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📊 Available Commands",
            value=(
                "• `/marketplace setup:True` - Initialize marketplace\n"
                "• View active listings and manage content\n"
                "• Monitor user reputation scores\n"
                "• Moderate marketplace activity"
            ),
            inline=False
        )

        return embed

    def create_setup_success_embed(self, channel_count: int) -> discord.Embed:
        """Create success message after setup."""
        embed = discord.Embed(
            title="✅ Marketplace Setup Complete!",
            description=(
                f"Successfully created {channel_count} marketplace channels.\n\n"
                "The marketplace is now ready for use. Users can create listings "
                "by clicking the buttons in each channel."
            ),
            color=self.COLORS['success'],
            timestamp=datetime.now(timezone.utc)
        )

        return embed

    def create_marketplace_embed(self, listing_type: str, zone: str, listings: List[Dict[str, Any]], page: int = 0) -> discord.Embed:
        """Create the main marketplace embed for a channel with pagination."""
        # Ensure we always use the correct title and color based on the provided listing_type
        title_emoji = "🔸" if listing_type.upper() == "WTS" else "🔹"
        color = self.COLORS['wts'] if listing_type.upper() == "WTS" else self.COLORS['wtb']

        # Calculate pagination
        items_per_page = 10
        total_pages = max(1, (len(listings) + items_per_page - 1) // items_per_page)
        page = max(0, min(page, total_pages - 1))
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_listings = listings[start_idx:end_idx]

        page_info = f" (Page {page + 1}/{total_pages})" if total_pages > 1 else ""

        embed = discord.Embed(
            title=f"{title_emoji} {listing_type} - {zone.title()}{page_info}",
            description=f"Active {listing_type} listings for {zone} content",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )

        if not listings:
            embed.add_field(
                name="📝 No Active Listings",
                value=f"No {listing_type} listings currently available for {zone}.\nBe the first to create one!",
                inline=False
            )
        elif not page_listings:
            embed.add_field(
                name="📝 No Listings on This Page",
                value="Use the navigation buttons to browse other pages.",
                inline=False
            )
        else:
            # Group listings by subcategory, with additional validation
            grouped = {}
            for listing in page_listings:
                # Skip listings that don't match the expected listing type
                if listing.get('listing_type', '').upper() != listing_type.upper():
                    logger.warning(f"Skipping mismatched listing in embed: expected {listing_type}, got {listing.get('listing_type')}")
                    continue

                subcat = listing.get('subcategory', 'Other')
                if subcat not in grouped:
                    grouped[subcat] = []
                grouped[subcat].append(listing)

            # Add fields for each subcategory
            for subcat, subcat_listings in grouped.items():
                all_listings_text = []
                
                for listing in subcat_listings:
                    # Format listing with user info
                    user_mention = f"<@{listing['user_id']}>"
                    time_str = listing.get('scheduled_time').strftime("%B %d – %I%p").replace(" 0", " ").replace("AM", "AM").replace("PM", "PM") if listing.get('scheduled_time') else "Unknown"

                    # Build individual listing text
                    individual_listing = []
                    individual_listing.append(f"🧾 **{listing_type}** by {user_mention}")
                    individual_listing.append(f"⏰ **Time:** {time_str}")

                    # Handle items and queues
                    if listing.get('queued_items'):
                        individual_listing.append("📦 **Item:**")
                        if listing['item'].lower() == "all items":
                            # Show queued items for "All Items" listings
                            for item_name, user_ids in listing['queued_items'].items():
                                user_mentions = [f"<@{uid}>" for uid in user_ids]
                                item_line = f"> **{item_name}** – **Queue:** {' • '.join(user_mentions)}"
                                individual_listing.append(item_line)
                        else:
                            # Show queue for specific item
                            user_mentions = [f"<@{uid}>" for uid in listing['queued_items'].get(listing['item'], [])]
                            item_line = f"> **{listing['item']}"
                            if listing['quantity'] > 1:
                                item_line += f" ×{listing['quantity']}"
                            item_line += "**"
                            if user_mentions:
                                item_line += f" – **Queue:** {' • '.join(user_mentions)}"
                            individual_listing.append(item_line)
                    else:
                        item_line = f"📦 **Item:** {listing['item']}"
                        if listing['quantity'] > 1:
                            item_line += f" ×{listing['quantity']}"
                        individual_listing.append(item_line)

                    if listing.get('notes'):
                        individual_listing.append(f"📝 **Notes:** {listing['notes']}")

                    # Add reputation if available
                    if listing.get('reputation_avg') and float(listing['reputation_avg']) > 0:
                        rep_stars = "⭐" * min(5, int(float(listing['reputation_avg'])))
                        individual_listing.append(f"{rep_stars} {float(listing['reputation_avg']):.1f}")

                    # Join this listing's lines and add to all listings
                    all_listings_text.append("\n".join(individual_listing))

                # Create the field with all listings for this subcategory
                embed.add_field(
                    name=f"📂 {subcat} ({len(subcat_listings)} {'item' if len(subcat_listings) == 1 else 'items'})",
                    value="\n\n".join(all_listings_text) if all_listings_text else "No listings",
                    inline=False
                )

        footer_text = f"Use the buttons below to manage your {listing_type} listings"
        if total_pages > 1:
            footer_text += f" • Page {page + 1} of {total_pages}"

        embed.set_footer(
            text=footer_text,
            icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
        )

        return embed

    def create_listing_confirmation_embed(self, listing_type: str, item: str, scheduled_time: datetime) -> discord.Embed:
        """Create confirmation embed for new listing."""
        embed = discord.Embed(
            title="✅ Listing Created Successfully!",
            description=f"Your {listing_type} entry for **{item}** has been added to the marketplace.",
            color=self.COLORS['success'],
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📅 Scheduled Time",
            value=f"<t:{int(scheduled_time.timestamp())}:F>",
            inline=True
        )

        embed.add_field(
            name="⏰ Expires In",
            value="14 days (with reminders)",
            inline=True
        )

        return embed

    def create_error_embed(self, message: str) -> discord.Embed:
        """Create error embed."""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=self.COLORS['error'],
            timestamp=datetime.now(timezone.utc)
        )

        return embed

    def create_reputation_embed(self, user: discord.User, reputation_data: Dict[str, Any]) -> discord.Embed:
        """Create reputation display embed."""
        embed = discord.Embed(
            title=f"⭐ Reputation - {user.display_name}",
            color=self.COLORS['info'],
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        avg_rating = reputation_data.get('average_rating', 0)
        total_ratings = reputation_data.get('total_ratings', 0)
        activity_score = reputation_data.get('activity_score', 0)

        # Star display
        stars = "⭐" * int(avg_rating) + "☆" * (5 - int(avg_rating))

        embed.add_field(
            name="📊 Overall Rating",
            value=f"{stars} ({avg_rating:.1f}/5.0)\nBased on {total_ratings} ratings",
            inline=True
        )

        embed.add_field(
            name="📈 Activity Score",
            value=f"{activity_score} points",
            inline=True
        )

        return embed