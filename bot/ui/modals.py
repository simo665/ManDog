"""
Discord modals for user input in the marketplace bot.
"""

import discord
from typing import Dict, Any
import logging
from datetime import datetime, timezone

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
        await interaction.response.send_message(
            f"✅ Date selected: {select.values[0]}\nNow choose a time...",
            ephemeral=True
        )

    @discord.ui.select(placeholder="Choose a time...")
    async def time_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle time selection."""
        self.listing_data['time'] = select.values[0]

        # If both date and time are selected, create the listing
        if 'date' in self.listing_data and 'time' in self.listing_data:
            await interaction.response.defer()
            await self.create_listing(interaction)
        else:
            await interaction.response.send_message(
                f"✅ Time selected: {select.values[0]}\nPlease select a date first.",
                ephemeral=True
            )

    @discord.ui.button(label="Custom Time", style=discord.ButtonStyle.secondary)
    async def custom_time_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle custom time input."""
        modal = CustomTimeModal(self.bot, self.listing_data)
        await interaction.response.send_modal(modal)

    async def create_listing(self, interaction: discord.Interaction):
        """Create the final listing."""
        try:
            # Combine date and time
            from datetime import datetime

            datetime_str = f"{self.listing_data['date']} {self.listing_data['time']}"
            scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

            # Use marketplace service to create listing and trigger matching
            from bot.services.marketplace import MarketplaceService
            marketplace_service = MarketplaceService(self.bot)
            listing_id = await marketplace_service.create_listing(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                listing_data={
                    **self.listing_data,
                    'scheduled_time': scheduled_time
                }
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

                await interaction.followup.send(embed=embed, ephemeral=True)

                # Refresh the original marketplace embed
                await self.refresh_original_embed_custom(interaction)
                logger.info(f"📝 MODAL DEBUG: Created listing with ID: {listing_id}")
            else:
                await interaction.followup.send(
                    "❌ Failed to create listing",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error creating listing: {e}")
            await interaction.followup.send(
                "❌ An error occurred while creating the listing",
                ephemeral=True
            )

    async def refresh_marketplace_channel(self, interaction: discord.Interaction):
        """Refresh the marketplace channel embed."""
        # This would update the main marketplace message in the channel
        pass

    async def refresh_original_embed(self, interaction: discord.Interaction):
        """Refresh the original marketplace embed with updated listings."""
        try:
            # The interaction is happening in the marketplace channel
            channel = interaction.channel

            if not channel:
                logger.warning("Could not get channel from interaction")
                return

            # Fetch the first (and should be only) message in the channel
            try:
                messages = [message async for message in channel.history(limit=1)]
                if not messages:
                    logger.warning(f"No messages found in channel {channel.name}")
                    return

                message = messages[0]
            except discord.Forbidden:
                logger.warning(f"No permission to read message history in {channel.name}")
                return
            except Exception as e:
                logger.error(f"Error fetching message from {channel.name}: {e}")
                return

            # Get updated listings
            listings = await self.bot.db_manager.get_zone_listings(
                interaction.guild.id,
                self.listing_data['listing_type'],
                self.listing_data['zone']
            )

            # Create updated embed
            from bot.ui.embeds import MarketplaceEmbeds
            embeds = MarketplaceEmbeds()
            updated_embed = embeds.create_marketplace_embed(
                self.listing_data['listing_type'],
                self.listing_data['zone'],
                listings,
                0  # Reset to first page
            )

            # Create updated view
            from bot.ui.views import MarketplaceView
            updated_view = MarketplaceView(
                self.bot,
                self.listing_data['listing_type'],
                self.listing_data['zone'],
                0  # Reset to first page
            )

            # Update the original marketplace message
            await message.edit(embed=updated_embed, view=updated_view)
            logger.info(f"Successfully refreshed marketplace embed for {channel.name}")

        except Exception as e:
            logger.error(f"Error refreshing original embed: {e}")

    async def refresh_original_embed_custom(self, interaction: discord.Interaction):
        """Refresh the original marketplace embed with updated listings."""
        try:
            # The interaction is happening in the marketplace channel
            channel = interaction.channel

            if not channel:
                logger.warning("Could not get channel from interaction")
                return

            # Fetch the first (and should be only) message in the channel
            try:
                messages = [message async for message in channel.history(limit=1)]
                if not messages:
                    logger.warning(f"No messages found in channel {channel.name}")
                    return

                message = messages[0]
            except discord.Forbidden:
                logger.warning(f"No permission to read message history in {channel.name}")
                return
            except Exception as e:
                logger.error(f"Error fetching message from {channel.name}: {e}")
                return

            # Get updated listings
            listings = await self.bot.db_manager.get_zone_listings(
                interaction.guild.id,
                self.listing_data['listing_type'],
                self.listing_data['zone']
            )

            # Create updated embed
            from bot.ui.embeds import MarketplaceEmbeds
            embeds = MarketplaceEmbeds()
            updated_embed = embeds.create_marketplace_embed(
                self.listing_data['listing_type'],
                self.listing_data['zone'],
                listings,
                0  # Reset to first page
            )

            # Create updated view
            from bot.ui.views import MarketplaceView
            updated_view = MarketplaceView(
                self.bot,
                self.listing_data['listing_type'],
                self.listing_data['zone'],
                0  # Reset to first page
            )

            # Update the original marketplace message
            await message.edit(embed=updated_embed, view=updated_view)
            logger.info(f"Successfully refreshed marketplace embed for {channel.name}")

        except Exception as e:
            logger.error(f"Error refreshing original embed: {e}")

class ListingModal(discord.ui.Modal):
    """Modal for creating a new listing (legacy - use QuantityNotesModal instead)."""

    def __init__(self, bot, listing_type: str, zone: str, subcategory: str):
        super().__init__(title=f"Create {listing_type} Listing")
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.subcategory = subcategory

        # Add item selection field with proper style
        self.item_input = discord.ui.TextInput(
            label="Item Name",
            placeholder="Enter item name",
            max_length=200,
            required=True,
            style=discord.TextStyle.short
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
            default="1",
            style=discord.TextStyle.short
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

            # Show date/time selection view
            view = DateTimeSelectView(self.bot, self.listing_data)
            
            embed = discord.Embed(
                title="📅 Schedule Your Listing",
                description=f"When would you like to be available for **{self.listing_data['item']}**?",
                color=0x3B82F6,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="🎯 Item",
                value=self.listing_data['item'],
                inline=True
            )
            
            embed.add_field(
                name="📦 Quantity", 
                value=str(quantity),
                inline=True
            )
            
            if self.listing_data['notes']:
                embed.add_field(
                    name="📝 Notes",
                    value=self.listing_data['notes'][:200],
                    inline=False
                )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in quantity/notes modal submission: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your listing",
                ephemeral=True
            )

class CustomTimeModal(discord.ui.Modal):
    """Modal for custom date and time input."""

    def __init__(self, bot, listing_data: Dict[str, Any]):
        super().__init__(title="Custom Date and Time")
        self.bot = bot
        self.listing_data = listing_data

        self.date_input = discord.ui.TextInput(
            label="Date (YYYY-MM-DD)",
            placeholder="2024-12-25",
            max_length=10,
            required=True,
            style=discord.TextStyle.short
        )

        self.time_input = discord.ui.TextInput(
            label="Time (HH:MM)",
            placeholder="14:30",
            max_length=5,
            required=True,
            style=discord.TextStyle.short
        )

        self.add_item(self.date_input)
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle custom time submission."""
        try:
            # Validate date format
            from datetime import datetime

            date_str = self.date_input.value
            time_str = self.time_input.value

            # Try to parse the datetime
            datetime_str = f"{date_str} {time_str}"
            scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

            # Check if it's in the future
            if scheduled_time <= datetime.now():
                await interaction.response.send_message(
                    "❌ Please select a future date and time",
                    ephemeral=True
                )
                return

            # Use marketplace service to create listing and trigger matching
            from bot.services.marketplace import MarketplaceService
            marketplace_service = MarketplaceService(self.bot)
            listing_id = await marketplace_service.create_listing(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                listing_data={
                    **self.listing_data,
                    'scheduled_time': scheduled_time
                }
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

                await interaction.response.send_message(embed=embed, ephemeral=True)

                # Refresh the original marketplace embed directly
                await self.refresh_original_embed_custom(interaction)
            else:
                await interaction.response.send_message(
                    "❌ Failed to create listing",
                    ephemeral=True
                )

        except ValueError as e:
            await interaction.response.send_message(
                "❌ Invalid date/time format. Please use YYYY-MM-DD for date and HH:MM for time",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in custom time modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while creating the listing",
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