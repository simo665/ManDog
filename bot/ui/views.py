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
    
    def __init__(self, bot, listing_type: str, zone: str):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.embeds = MarketplaceEmbeds()
        
        # Customize button labels based on type
        self.add_button.label = f"Add {listing_type}"
        self.remove_button.label = f"Remove {listing_type}"
    
    @discord.ui.button(label="Add WTS", style=discord.ButtonStyle.green, emoji="➕")
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle add listing button."""
        await self.start_listing_flow(interaction)
    
    @discord.ui.button(label="Remove WTS", style=discord.ButtonStyle.red, emoji="➖")
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle remove listing button."""
        await self.show_remove_options(interaction)
    
    async def start_listing_flow(self, interaction: discord.Interaction):
        """Start the listing creation flow."""
        try:
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
            
        except Exception as e:
            logger.error(f"Error starting listing flow: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while starting the listing process",
                ephemeral=True
            )
    
    async def show_remove_options(self, interaction: discord.Interaction):
        """Show user's listings for removal."""
        try:
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
            
        except Exception as e:
            logger.error(f"Error showing remove options: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while loading your listings",
                ephemeral=True
            )

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
        
        # Create dropdown with items
        options = [discord.SelectOption(label="All Items", value="All Items")]
        options.extend([
            discord.SelectOption(label=item, value=item)
            for item in items[:24]  # Discord limit
        ])
        
        self.item_select.options = options
    
    @discord.ui.select(placeholder="Choose an item...")
    async def item_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle item selection."""
        item = select.values[0]
        
        # Show quantity and notes modal
        modal = QuantityNotesModal(
            self.bot, self.listing_type, self.zone, 
            self.subcategory, item
        )
        
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
            # Remove the listing from database
            success = await self.bot.db_manager.remove_listing(listing_id, interaction.user.id)
            
            if success:
                await interaction.response.send_message(
                    "✅ Listing removed successfully!",
                    ephemeral=True
                )
                
                # Update the marketplace embed
                # This would trigger a refresh of the marketplace channel
                await self.refresh_marketplace_embed(interaction)
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
        # This would be implemented to update the main marketplace message
        pass

class DateTimeSelectView(discord.ui.View):
    """View for selecting date and time."""
    
    def __init__(self, bot, listing_data: Dict[str, Any]):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_data = listing_data
        
        # Add date options (today + 14 days)
        from datetime import datetime, timedelta
        
        date_options = []
        for i in range(15):  # 0-14 days ahead
            date = datetime.now() + timedelta(days=i)
            label = date.strftime("%A, %B %d")
            if i == 0:
                label += " (Today)"
            elif i == 1:
                label += " (Tomorrow)"
            
            date_options.append(
                discord.SelectOption(
                    label=label,
                    value=date.strftime("%Y-%m-%d")
                )
            )
        
        self.date_select.options = date_options[:25]  # Discord limit
        
        # Add time options (00:00 to 23:00)
        time_options = []
        for hour in range(24):
            time_str = f"{hour:02d}:00"
            time_options.append(
                discord.SelectOption(label=time_str, value=time_str)
            )
        
        self.time_select.options = time_options
    
    @discord.ui.select(placeholder="Choose a date...")
    async def date_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle date selection."""
        self.listing_data['date'] = select.values[0]
        await interaction.response.defer()
    
    @discord.ui.select(placeholder="Choose a time...")
    async def time_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle time selection."""
        self.listing_data['time'] = select.values[0]
        
        # If both date and time are selected, create the listing
        if 'date' in self.listing_data and 'time' in self.listing_data:
            await self.create_listing(interaction)
    
    @discord.ui.button(label="Custom Time", style=discord.ButtonStyle.secondary)
    async def custom_time_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle custom time input."""
        # Would show a modal for custom time input
        pass
    
    async def create_listing(self, interaction: discord.Interaction):
        """Create the final listing."""
        try:
            # Combine date and time
            from datetime import datetime
            
            datetime_str = f"{self.listing_data['date']} {self.listing_data['time']}"
            scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            
            # Store listing in database
            listing_id = await self.bot.db_manager.create_listing(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                listing_type=self.listing_data['listing_type'],
                zone=self.listing_data['zone'],
                subcategory=self.listing_data['subcategory'],
                item=self.listing_data['item'],
                quantity=self.listing_data['quantity'],
                notes=self.listing_data['notes'],
                scheduled_time=scheduled_time
            )
            
            if listing_id:
                # Send confirmation
                embeds = MarketplaceEmbeds()
                embed = embeds.create_listing_confirmation_embed(
                    self.listing_data['listing_type'],
                    self.listing_data['item'],
                    scheduled_time
                )
                
                await interaction.edit_original_response(embed=embed, view=None)
                
                # Refresh marketplace embed
                await self.refresh_marketplace_channel(interaction)
            else:
                await interaction.edit_original_response(
                    content="❌ Failed to create listing",
                    embed=None,
                    view=None
                )
                
        except Exception as e:
            logger.error(f"Error creating listing: {e}")
            await interaction.edit_original_response(
                content="❌ An error occurred while creating the listing",
                embed=None,
                view=None
            )
    
    async def refresh_marketplace_channel(self, interaction: discord.Interaction):
        """Refresh the marketplace channel embed."""
        # This would update the main marketplace message in the channel
        pass
