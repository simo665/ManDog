"""
Discord modals for user input in the marketplace bot.
"""

import discord
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

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
                from bot.ui.embeds import MarketplaceEmbeds
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

class ListingModal(discord.ui.Modal):
    """Modal for creating a new listing."""
    
    def __init__(self, bot, listing_type: str, zone: str, subcategory: str):
        super().__init__(title=f"Create {listing_type} Listing")
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.subcategory = subcategory
        
        # Add item selection field
        from config.ffxi_data import get_subcategory_items
        items = get_subcategory_items(zone, subcategory)
        
        self.item_input = discord.ui.TextInput(
            label="Item Name",
            placeholder=f"Enter item name (e.g., {items[1] if len(items) > 1 else 'item name'})",
            max_length=200,
            required=True
        )
        
        self.add_item(self.item_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            item_name = self.item_input.value
            
            # Create listing data for next step
            listing_data = {
                'listing_type': self.listing_type,
                'zone': self.zone,
                'subcategory': self.subcategory,
                'item': item_name
            }
            
            # Show quantity and notes modal
            modal = QuantityNotesModal(self.bot, listing_data)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error in listing modal submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your listing",
                ephemeral=True
            )

class QuantityNotesModal(discord.ui.Modal):
    """Modal for quantity and notes input."""
    
    def __init__(self, bot, listing_data: Dict[str, Any]):
        super().__init__(title="Listing Details")
        self.bot = bot
        self.listing_data = listing_data
        
        self.quantity_input = discord.ui.TextInput(
            label="Quantity",
            placeholder="How many? (default: 1)",
            max_length=10,
            required=False,
            default="1"
        )
        
        self.notes_input = discord.ui.TextInput(
            label="Notes (Optional)",
            placeholder="Any additional details...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.quantity_input)
        self.add_item(self.notes_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle quantity/notes submission."""
        try:
            # Parse quantity
            quantity_str = self.quantity_input.value or "1"
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    quantity = 1
            except ValueError:
                quantity = 1
            
            # Store data
            self.listing_data['quantity'] = quantity
            self.listing_data['notes'] = self.notes_input.value
            
            # Show date/time selection
            view = DateTimeSelectView(self.bot, listing_data)
            embed = discord.Embed(
                title="📅 Pick Date and Time",
                description="Select when you want this listing to be active:",
                color=0x1E40AF
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in quantity/notes modal submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your listing",
                ephemeral=True
            )

class ReputationModal(discord.ui.Modal):
    """Modal for submitting reputation ratings."""
    
    def __init__(self, bot, target_user_id: int, listing_id: int):
        super().__init__(title="Rate User")
        self.bot = bot
        self.target_user_id = target_user_id
        self.listing_id = listing_id
        
        self.rating_input = discord.ui.TextInput(
            label="Rating (1-5 stars)",
            placeholder="Enter a rating from 1 to 5",
            max_length=1,
            required=True
        )
        
        self.comment_input = discord.ui.TextInput(
            label="Comment (Optional)",
            placeholder="Leave a comment about your experience",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.rating_input)
        self.add_item(self.comment_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle reputation submission."""
        try:
            # Validate rating
            rating = int(self.rating_input.value)
            if rating < 1 or rating > 5:
                await interaction.response.send_message(
                    "❌ Rating must be between 1 and 5",
                    ephemeral=True
                )
                return
            
            # Submit rating
            success = await self.bot.db_manager.add_reputation(
                rater_id=interaction.user.id,
                target_id=self.target_user_id,
                listing_id=self.listing_id,
                rating=rating,
                comment=self.comment_input.value
            )
            
            if success:
                await interaction.response.send_message(
                    f"✅ Thank you! You rated this user {rating} stars.",
                    ephemeral=True
                )
                
                # Update target user's reputation
                await self.bot.db_manager.update_user_reputation(self.target_user_id)
            else:
                await interaction.response.send_message(
                    "❌ Could not submit rating. You may have already rated this user for this listing.",
                    ephemeral=True
                )
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number between 1 and 5",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error submitting reputation: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while submitting your rating",
                ephemeral=True
            )