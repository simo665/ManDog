"""
Discord modals for user input in the marketplace bot.
"""

import discord
from typing import Dict, Any
import logging

# Removed circular import - DateTimeSelectView is now defined in this file

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
        
        # Add input fields
        self.item_input = discord.ui.TextInput(
            label="Item Name",
            placeholder="Enter the item name or 'All Items'",
            max_length=100,
            required=True
        )
        
        self.quantity_input = discord.ui.TextInput(
            label="Quantity",
            placeholder="Enter quantity (default: 1)",
            default="1",
            max_length=10,
            required=False
        )
        
        self.notes_input = discord.ui.TextInput(
            label="Notes/Price",
            placeholder="Additional notes, price, or special requirements",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.item_input)
        self.add_item(self.quantity_input)
        self.add_item(self.notes_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            # Validate quantity
            quantity = 1
            if self.quantity_input.value:
                try:
                    quantity = int(self.quantity_input.value)
                    if quantity < 1:
                        quantity = 1
                except ValueError:
                    quantity = 1
            
            # Prepare listing data
            listing_data = {
                'listing_type': self.listing_type,
                'zone': self.zone,
                'subcategory': self.subcategory,
                'item': self.item_input.value,
                'quantity': quantity,
                'notes': self.notes_input.value
            }
            
            # Show date/time selection
            view = DateTimeSelectView(self.bot, listing_data)
            
            embed = discord.Embed(
                title="📅 Pick Date and Time",
                description="Select when you want this listing to be active:",
                color=0x1E40AF
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in listing modal submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your listing",
                ephemeral=True
            )

class QuantityNotesModal(discord.ui.Modal):
    """Simplified modal for quantity and notes only."""
    
    def __init__(self, bot, listing_type: str, zone: str, subcategory: str, item: str):
        super().__init__(title=f"Listing Details")
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.subcategory = subcategory
        self.item = item
        
        # Add input fields
        self.quantity_input = discord.ui.TextInput(
            label="Quantity",
            placeholder="Enter quantity (default: 1)",
            default="1",
            max_length=10,
            required=False
        )
        
        self.notes_input = discord.ui.TextInput(
            label="Notes/Price",
            placeholder="Additional notes, price, or special requirements",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.quantity_input)
        self.add_item(self.notes_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            # Validate quantity
            quantity = 1
            if self.quantity_input.value:
                try:
                    quantity = int(self.quantity_input.value)
                    if quantity < 1:
                        quantity = 1
                except ValueError:
                    quantity = 1
            
            # Prepare listing data
            listing_data = {
                'listing_type': self.listing_type,
                'zone': self.zone,
                'subcategory': self.subcategory,
                'item': self.item,
                'quantity': quantity,
                'notes': self.notes_input.value
            }
            
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

class CustomTimeModal(discord.ui.Modal):
    """Modal for custom time input."""
    
    def __init__(self, callback_function):
        super().__init__(title="Custom Time")
        self.callback_function = callback_function
        
        self.time_input = discord.ui.TextInput(
            label="Time (HH:MM)",
            placeholder="Enter time in HH:MM format (e.g., 15:30)",
            max_length=5,
            required=True
        )
        
        self.add_item(self.time_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle custom time submission."""
        try:
            time_str = self.time_input.value
            
            # Validate time format
            if ":" not in time_str or len(time_str) != 5:
                await interaction.response.send_message(
                    "❌ Invalid time format. Please use HH:MM format.",
                    ephemeral=True
                )
                return
            
            hour_str, minute_str = time_str.split(":")
            hour = int(hour_str)
            minute = int(minute_str)
            
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                await interaction.response.send_message(
                    "❌ Invalid time. Hour must be 0-23, minute must be 0-59.",
                    ephemeral=True
                )
                return
            
            # Call the callback function with the validated time
            await self.callback_function(interaction, time_str)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid time format. Please use HH:MM format with numbers only.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in custom time modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the custom time",
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
            
            # Store reputation in database
            success = await self.bot.db_manager.add_reputation(
                rater_id=interaction.user.id,
                target_id=self.target_user_id,
                listing_id=self.listing_id,
                rating=rating,
                comment=self.comment_input.value
            )
            
            if success:
                await interaction.response.send_message(
                    f"✅ Thank you for rating this user {rating} star{'s' if rating != 1 else ''}!",
                    ephemeral=True
                )
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
