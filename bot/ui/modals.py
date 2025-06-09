"""
Discord modals for user input in the marketplace bot.
"""

import discord
from typing import Dict, Any
import logging

from bot.ui.views import DateTimeSelectView

logger = logging.getLogger(__name__)

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
