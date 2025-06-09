"""
Discord UI views and buttons for the marketplace bot.
"""

import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any
import logging

from bot.ui.modals import ListingModal, QuantityNotesModal
from bot.ui.embeds import MarketplaceEmbeds
from config.ffxi_data import get_zone_subcategories, get_subcategory_items

logger = logging.getLogger(__name__)

class SetupView(discord.ui.View):
    """View for marketplace setup."""
    
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @discord.ui.button(label="🏗️ Setup Marketplace", style=discord.ButtonStyle.primary)
    async def setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle setup button click."""
        await interaction.response.defer(ephemeral=True)
        
        # Import here to avoid circular imports
        from bot.commands.marketplace import MarketplaceCommands
        
        # Get the marketplace commands cog
        marketplace_cog = self.bot.get_cog('MarketplaceCommands')
        if marketplace_cog:
            await marketplace_cog.setup_marketplace_channels(interaction.guild, interaction)
        else:
            await interaction.followup.send("❌ Marketplace commands not available", ephemeral=True)

class MarketplaceView(discord.ui.View):
    """Persistent view for marketplace channels."""
    
    def __init__(self, bot, listing_type: str, zone: str, current_page: int = 0):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.current_page = current_page
        self.embeds = MarketplaceEmbeds()
        
        # Customize button labels based on type
        self.add_button.label = f"Add {listing_type}"
        self.remove_button.label = f"Remove {listing_type}"
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="marketplace_prev", row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle previous page button."""
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="marketplace_next", row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle next page button."""
        # Get current listings to check if there's a next page
        listings = await self.bot.db_manager.get_zone_listings(
            interaction.guild.id, self.listing_type, self.zone
        )
        max_pages = max(1, (len(listings) + 9) // 10)  # 10 items per page
        
        if self.current_page < max_pages - 1:
            self.current_page += 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Add WTS", style=discord.ButtonStyle.green, emoji="➕", custom_id="marketplace_add", row=1)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle add listing button."""
        await self.start_listing_flow(interaction)
    
    @discord.ui.button(label="Remove WTS", style=discord.ButtonStyle.red, emoji="➖", custom_id="marketplace_remove", row=1)
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle remove listing button."""
        await self.show_remove_options(interaction)
    
    async def start_listing_flow(self, interaction: discord.Interaction):
        """Start the listing creation flow."""
        try:
            # Check if interaction is already acknowledged
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Interaction has expired. Please try again.",
                    ephemeral=True
                )
                return
            
            # Validate zone name
            if not self.zone or self.zone == "unknown":
                await interaction.response.send_message(
                    "❌ Invalid zone configuration. Please contact an administrator.",
                    ephemeral=True
                )
                return
                
            # Get subcategories for this zone
            subcategories = get_zone_subcategories(self.zone)
            
            if not subcategories:
                await interaction.response.send_message(
                    f"❌ No subcategories configured for {self.zone}",
                    ephemeral=True
                )
                return
            
            # Create dropdown for subcategory selection
            view = SubcategorySelectView(self.bot, self.listing_type, self.zone, subcategories)
            
            embed = discord.Embed(
                title=f"📂 Select Subcategory",
                description=f"Choose a subcategory for your {self.listing_type} entry in {self.zone.title()}:",
                color=self.embeds.COLORS['primary']
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except discord.errors.NotFound:
            logger.warning("Interaction not found - likely expired")
        except discord.errors.HTTPException as e:
            if "already been acknowledged" in str(e):
                logger.warning("Interaction already acknowledged")
            else:
                logger.error(f"HTTP error in listing flow: {e}")
        except Exception as e:
            logger.error(f"Error starting listing flow: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while starting the listing process",
                        ephemeral=True
                    )
            except:
                pass
    
    async def update_embed(self, interaction: discord.Interaction):
        """Update the marketplace embed with current page."""
        try:
            # Get current listings
            listings = await self.bot.db_manager.get_zone_listings(
                interaction.guild.id, self.listing_type, self.zone
            )
            
            # Create updated embed
            embed = self.embeds.create_marketplace_embed(
                self.listing_type, self.zone, listings, self.current_page
            )
            
            # Update the view with current page
            new_view = MarketplaceView(self.bot, self.listing_type, self.zone, self.current_page)
            
            await interaction.response.edit_message(embed=embed, view=new_view)
            
        except Exception as e:
            logger.error(f"Error updating embed: {e}")
            await interaction.response.defer()

    async def show_remove_options(self, interaction: discord.Interaction):
        """Show user's listings for removal."""
        try:
            # Check if interaction is already acknowledged
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Interaction has expired. Please try again.",
                    ephemeral=True
                )
                return
            
            # Validate zone name
            if not self.zone or self.zone == "unknown":
                await interaction.response.send_message(
                    "❌ Invalid zone configuration. Please contact an administrator.",
                    ephemeral=True
                )
                return
                
            # Get user's active listings for this zone
            listings = await self.bot.db_manager.get_user_listings(
                interaction.user.id,
                interaction.guild.id,
                self.listing_type,
                self.zone
            )
            
            if not listings:
                await interaction.response.send_message(
                    f"❌ You don't have any active {self.listing_type} listings in {self.zone.title()}",
                    ephemeral=True
                )
                return
            
            # Create removal view
            view = RemoveListingView(self.bot, listings)
            
            embed = discord.Embed(
                title=f"🗑️ Remove {self.listing_type} Listings",
                description="Select which listing you want to remove:",
                color=self.embeds.COLORS['warning']
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except discord.errors.NotFound:
            logger.warning("Interaction not found - likely expired")
        except discord.errors.HTTPException as e:
            if "already been acknowledged" in str(e):
                logger.warning("Interaction already acknowledged")
            else:
                logger.error(f"HTTP error in remove options: {e}")
        except Exception as e:
            logger.error(f"Error showing remove options: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while loading your listings",
                        ephemeral=True
                    )
            except:
                pass

class SubcategorySelectView(discord.ui.View):
    """View for selecting subcategory."""
    
    def __init__(self, bot, listing_type: str, zone: str, subcategories: List[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        
        # Create dropdown with subcategories
        options = [
            discord.SelectOption(label=subcat, value=subcat)
            for subcat in subcategories
        ]
        
        self.subcategory_select.options = options
    
    @discord.ui.select(placeholder="Choose a subcategory...")
    async def subcategory_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle subcategory selection."""
        subcategory = select.values[0]
        
        # Get items for this subcategory
        items = get_subcategory_items(self.zone, subcategory)
        
        if not items:
            await interaction.response.send_message(
                f"❌ No items configured for {subcategory}",
                ephemeral=True
            )
            return
        
        # Show item selection
        view = ItemSelectView(self.bot, self.listing_type, self.zone, subcategory, items)
        
        embed = discord.Embed(
            title=f"🎯 Select Item",
            description=f"Choose an item (or 'All Items') for **{subcategory}**:",
            color=0x1E40AF
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

class ItemSelectView(discord.ui.View):
    """View for selecting specific item."""
    
    def __init__(self, bot, listing_type: str, zone: str, subcategory: str, items: List[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.subcategory = subcategory
        
        # Create dropdown with items (ensure unique values)
        unique_items = []
        seen_values = set()
        
        for item in items[:25]:  # Discord limit of 25 options
            if item not in seen_values:
                unique_items.append(item)
                seen_values.add(item)
        
        options = [
            discord.SelectOption(label=item, value=item)
            for item in unique_items
        ]
        
        self.item_select.options = options
    
    @discord.ui.select(placeholder="Choose an item...")
    async def item_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle item selection."""
        item = select.values[0]
        
        # Create listing data for next step
        listing_data = {
            'listing_type': self.listing_type,
            'zone': self.zone,
            'subcategory': self.subcategory,
            'item': item
        }
        
        # Show quantity and notes modal
        from bot.ui.modals import QuantityNotesModal
        modal = QuantityNotesModal(self.bot, listing_data)
        
        await interaction.response.send_modal(modal)

class RemoveListingView(discord.ui.View):
    """View for removing user's listings."""
    
    def __init__(self, bot, listings: List[Dict[str, Any]]):
        super().__init__(timeout=300)
        self.bot = bot
        
        # Create dropdown with user's listings
        options = []
        for listing in listings[:25]:  # Discord limit
            label = f"{listing['item']} - {listing['subcategory']}"
            if len(label) > 100:
                label = label[:97] + "..."
            
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(listing['id']),
                    description=listing.get('notes', '')[:100] if listing.get('notes') else None
                )
            )
        
        self.listing_select.options = options
    
    @discord.ui.select(placeholder="Choose a listing to remove...")
    async def listing_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle listing removal."""
        listing_id = int(select.values[0])
        
        try:
            # Use the marketplace service to remove the listing
            from bot.services.marketplace import MarketplaceService
            marketplace_service = MarketplaceService(self.bot)
            
            success = await marketplace_service.remove_listing(listing_id, interaction.user.id)
            
            if success:
                await interaction.response.send_message(
                    "✅ Listing removed successfully!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Could not remove listing. It may have already been removed.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error removing listing: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while removing the listing",
                ephemeral=True
            )
    
    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh the marketplace embed in the channel."""
        try:
            # Get the marketplace service
            from bot.services.marketplace import MarketplaceService
            marketplace_service = MarketplaceService(self.bot)
            
            # Find the marketplace channel for this guild and zone
            marketplace_channels = await self.bot.db_manager.execute_query(
                "SELECT channel_id FROM marketplace_channels WHERE guild_id = $1",
                interaction.guild.id
            )
            
            # Refresh all marketplace embeds
            for channel_data in marketplace_channels:
                await marketplace_service.refresh_marketplace_embed(
                    interaction.guild.id, channel_data['channel_id']
                )
                
        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

# DateTimeSelectView moved to modals.py to fix circular import
