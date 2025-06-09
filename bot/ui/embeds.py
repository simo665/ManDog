"""
Embed creation utilities for the marketplace bot.
"""

import discord
from datetime import datetime, timezone
from typing import List, Dict, Any

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
    
    def create_marketplace_embed(self, listing_type: str, zone: str, listings: List[Dict[str, Any]]) -> discord.Embed:
        """Create the main marketplace embed for a channel."""
        title_emoji = "🔸" if listing_type == "WTS" else "🔹"
        color = self.COLORS['wts'] if listing_type == "WTS" else self.COLORS['wtb']
        
        embed = discord.Embed(
            title=f"{title_emoji} {listing_type} - {zone.title()}",
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
        else:
            # Group listings by subcategory
            grouped = {}
            for listing in listings:
                subcat = listing.get('subcategory', 'Other')
                if subcat not in grouped:
                    grouped[subcat] = []
                grouped[subcat].append(listing)
            
            # Add fields for each subcategory
            for subcat, subcat_listings in grouped.items():
                listing_text = []
                for listing in subcat_listings[:5]:  # Limit to 5 per subcategory
                    user_mention = f"<@{listing['user_id']}>"
                    item = listing.get('item', 'All Items')
                    quantity = listing.get('quantity', 1)
                    notes = listing.get('notes', '')
                    
                    listing_line = f"• {user_mention} - {item}"
                    if quantity > 1:
                        listing_line += f" (x{quantity})"
                    if notes:
                        listing_line += f" - {notes[:50]}{'...' if len(notes) > 50 else ''}"
                    
                    listing_text.append(listing_line)
                
                if len(subcat_listings) > 5:
                    listing_text.append(f"... and {len(subcat_listings) - 5} more")
                
                embed.add_field(
                    name=f"📂 {subcat}",
                    value="\n".join(listing_text) if listing_text else "No listings",
                    inline=False
                )
        
        embed.set_footer(
            text=f"Use the buttons below to manage your {listing_type} listings",
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
