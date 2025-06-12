from datetime import datetime, timezone
from config.ffxi_data import ZONE_DATA
# Import ordering views
from bot.ui.views_ordering import (
    OrderConfirmationView, OrderCompletionView, RatingView, 
    MatchSelectionView, QueueNotificationView
)
import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any
import logging
from bot.ui.modals import ListingModal, QuantityNotesModal
from bot.ui.embeds import MarketplaceEmbeds
import asyncio
from bot.utils.logger import logger
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class SetupView(discord.ui.View):
    """View for marketplace setup."""

    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot

    @discord.ui.button(label="🏗️ Setup Marketplace", style=discord.ButtonStyle.primary)
    async def setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle setup button click."""
        try:
            await interaction.response.defer(ephemeral=True)

            # Import here to avoid circular imports
            from bot.commands.marketplace import MarketplaceCommands

            # Get the marketplace commands cog
            marketplace_cog = self.bot.get_cog('MarketplaceCommands')
            if marketplace_cog:
                await marketplace_cog.setup_marketplace_channels(interaction.guild, interaction)
            else:
                await interaction.followup.send("❌ Marketplace commands not available", ephemeral=True)
        except discord.errors.NotFound:
            logger.warning("Setup interaction expired or not found")
        except Exception as e:
            logger.error(f"Error in setup button: {e}")
            try:
                await interaction.followup.send("❌ An error occurred during setup", ephemeral=True)
            except:
                pass

class MarketplaceView(discord.ui.View):
    """Persistent view for marketplace channels."""

    def __init__(self, bot, listing_type: str, zone: str, current_page: int = 0):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.current_page = current_page
        self.embeds = MarketplaceEmbeds()

        # Update custom_ids to include context
        self.prev_button.custom_id = f"marketplace_prev_{listing_type}_{zone}"
        self.next_button.custom_id = f"marketplace_next_{listing_type}_{zone}"
        self.add_button.custom_id = f"marketplace_add_{listing_type}_{zone}"
        self.remove_button.custom_id = f"marketplace_remove_{listing_type}_{zone}"

        # Customize button labels based on type
        self.add_button.label = f"Add {listing_type}"
        self.remove_button.label = f"Remove {listing_type}"

        # Add queue buttons for WTS embeds only
        if listing_type.upper() == "WTS":
            self.join_queue_button.custom_id = f"marketplace_queue_{listing_type}_{zone}"
            self.leave_queue_button.custom_id = f"marketplace_leave_queue_{listing_type}_{zone}"
        else:
            # Remove queue buttons for WTB embeds
            self.remove_item(self.join_queue_button)
            self.remove_item(self.leave_queue_button)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle previous page button."""
        try:
            if self.current_page > 0:
                self.current_page -= 1
                await self.update_embed(interaction)
            else:
                await interaction.response.defer()
        except Exception as e:
            logger.error(f"Error in prev button: {e}")
            await self.safe_defer(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle next page button."""
        try:
            # Get current listings to check if there's a next page
            listings = await self.get_listings_with_queues(interaction.guild.id)
            max_pages = max(1, (len(listings) + 9) // 10)  # 10 items per page

            if self.current_page < max_pages - 1:
                self.current_page += 1
                await self.update_embed(interaction)
            else:
                await interaction.response.defer()
        except Exception as e:
            logger.error(f"Error in next button: {e}")
            await self.safe_defer(interaction)

    @discord.ui.button(label="Add WTS", style=discord.ButtonStyle.green, emoji="➕", row=1)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle add listing button."""
        await self.start_listing_flow(interaction)

    @discord.ui.button(label="Remove WTS", style=discord.ButtonStyle.red, emoji="➖", row=1)
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle remove listing button."""
        await self.show_remove_options(interaction)

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.secondary, emoji="⏱️", row=2)
    async def join_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle join queue button for WTS listings."""
        try:
            # Only show queue button for WTS listings
            if self.listing_type.upper() != "WTS":
                await interaction.response.send_message(
                    "❌ Queue feature is only available for WTS (Want to Sell) listings.",
                    ephemeral=True
                )
                return

            # Get all available items from the items database for this zone
            available_items = await self.bot.db_manager.get_all_items_by_zone(self.zone)

            if not available_items:
                await interaction.response.send_message(
                    f"❌ No items available for {self.zone.title()}.",
                    ephemeral=True
                )
                return

            # Check if there are too many items for a dropdown (Discord limit is 25)
            if len(available_items) > 25:
                # Use search modal instead
                from bot.ui.modals import QueueSearchModal
                modal = QueueSearchModal(self.bot, self.zone)
                await interaction.response.send_modal(modal)
            else:
                # Use dropdown
                from bot.ui.modals import QueueSelectView
                view = QueueSelectView(self.bot, [], self.zone, available_items)

                embed = discord.Embed(
                    title="🔥 Join Queue",
                    description=f"Select an item to queue for in {self.zone.title()}:",
                    color=0xFF6B6B
                )

                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error opening queue selection: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while opening the queue selection.",
                        ephemeral=True
                    )
            except:
                pass

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def leave_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle leave queue button for WTS listings."""
        try:
            # Get user's current queue entries for this zone
            user_queues = await self.bot.db_manager.execute_query(
                """
                SELECT lq.listing_id, lq.item_name, l.user_id as seller_id
                FROM listing_queues lq
                JOIN listings l ON lq.listing_id = l.id
                WHERE lq.user_id = $1 AND l.zone = $2 AND l.active = TRUE
                """,
                interaction.user.id, self.zone
            )

            if not user_queues:
                await interaction.response.send_message(
                    f"❌ You are not queued for any items in {self.zone.title()}.",
                    ephemeral=True
                )
                return

            # Create dropdown for leaving queues
            from bot.ui.modals import LeaveQueueView
            view = LeaveQueueView(self.bot, user_queues, self.zone)

            embed = discord.Embed(
                title="❌ Leave Queue",
                description=f"Select which queue you want to leave in {self.zone.title()}:",
                color=0xFF4444
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error opening leave queue selection: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while opening the leave queue selection.",
                        ephemeral=True
                    )
            except:
                pass

    async def safe_defer(self, interaction: discord.Interaction):
        """Safely defer an interaction."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except:
            pass

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

            # Get channel information to ensure we have correct context
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT listing_type, zone FROM marketplace_channels WHERE channel_id = $1",
                interaction.channel.id
            )

            if channel_info:
                # Use the channel's actual configuration
                channel_data = channel_info[0]
                actual_listing_type = channel_data['listing_type']
                actual_zone = channel_data['zone']

                # Update instance variables with correct values
                self.listing_type = actual_listing_type
                self.zone = actual_zone

                logger.info(f"Updated view context: {self.listing_type} in {self.zone} for channel {interaction.channel.id}")

            # Validate zone name
            if not self.zone or self.zone == "unknown":
                await interaction.response.send_message(
                    "❌ Invalid zone configuration. Please contact an administrator.",
                    ephemeral=True
                )
                return

            # Get monsters for this zone from database
            monsters = await self.bot.db_manager.get_monsters_by_zone(self.zone)

            if not monsters:
                await interaction.response.send_message(
                    f"❌ No monsters configured for {self.zone}",
                    ephemeral=True
                )
                return

            # Create dropdown for monster selection
            view = MonsterSelectView(self.bot, self.listing_type, self.zone, monsters)

            embed = discord.Embed(
                title=f"📂 Select Monster",
                description=f"Choose a monster for your {self.listing_type} entry in {self.zone.title()}:",
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

    async def get_listings_with_queues(self, guild_id: int):
        """Get listings with their queue data."""
        listings = await self.bot.db_manager.get_zone_listings(
            guild_id, self.listing_type, self.zone
        )

        # Add queue data to each listing
        for listing in listings:
            if self.listing_type.upper() == "WTS":
                queues = await self.bot.db_manager.get_listing_queues(listing['id'])
                listing['queues'] = queues

        return listings

    async def update_embed(self, interaction: discord.Interaction):
        """Update the marketplace embed with current page."""
        try:
            # Get current listings with queue data
            listings = await self.get_listings_with_queues(interaction.guild.id)

            # Create updated embed
            embed = self.embeds.create_marketplace_embed(
                self.listing_type, self.zone, listings, self.current_page
            )

            # Update the view with current page
            new_view = MarketplaceView(self.bot, self.listing_type, self.zone, self.current_page)

            await interaction.response.edit_message(embed=embed, view=new_view)

        except Exception as e:
            logger.error(f"Error updating embed: {e}")
            await self.safe_defer(interaction)

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

            # Get channel information to ensure we have correct context
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT listing_type, zone FROM marketplace_channels WHERE channel_id = $1",
                interaction.channel.id
            )

            if channel_info:
                # Use the channel's actual configuration
                channel_data = channel_info[0]
                actual_listing_type = channel_data['listing_type']
                actual_zone = channel_data['zone']

                # Update instance variables with correct values
                self.listing_type = actual_listing_type
                self.zone = actual_zone

                logger.info(f"Updated view context: {self.listing_type} in {self.zone} for channel {interaction.channel.id}")

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
            view = RemoveListingView(self.bot, listings, self.listing_type, self.zone)

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

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh the marketplace embed in the channel."""
        try:
            # Get the specific marketplace channel for this listing type and zone
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = $2 AND zone = $3",
                interaction.guild.id, self.listing_type, self.zone
            )

            if not channel_info:
                logger.warning(f"No marketplace channel found for {self.listing_type} in {self.zone}")
                return

            channel_data = channel_info[0]
            channel = interaction.guild.get_channel(channel_data['channel_id'])

            if not channel:
                logger.warning(f"Channel {channel_data['channel_id']} not found")
                return

            # Get updated listings with queue data
            listings = await self.get_listings_with_queues(interaction.guild.id)

            # Create updated embed
            embeds = MarketplaceEmbeds()
            embed = embeds.create_marketplace_embed(
                self.listing_type, self.zone, listings, 0  # Reset to first page
            )

            # Create new view
            view = MarketplaceView(self.bot, self.listing_type, self.zone, 0)

            # Try to find and update the marketplace message
            message_id = channel_data.get('message_id')
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed, view=view)
                    return
                except discord.NotFound:
                    logger.warning(f"Marketplace message {message_id} not found")

            # If message_id doesn't work, search for the message
            async for message in channel.history(limit=50):
                if (message.author == self.bot.user and 
                    message.embeds and 
                    message.embeds[0].title and 
                    self.listing_type.upper() in message.embeds[0].title and
                    self.zone.lower() in message.embeds[0].title.lower()):
                    await message.edit(embed=embed, view=view)

                    # Update the stored message_id
                    await self.bot.db_manager.execute_command(
                        "UPDATE marketplace_channels SET message_id = $1 WHERE channel_id = $2",
                        message.id, channel.id
                    )
                    break

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class MonsterSelectView(discord.ui.View):
    """View for selecting monster/source."""

    def __init__(self, bot, listing_type: str, zone: str, monsters: List[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone

        # Create dropdown with monsters
        options = [
            discord.SelectOption(label=monster, value=monster)
            for monster in monsters[:25]  # Discord limit
        ]

        self.monster_select.options = options

    @discord.ui.select(placeholder="Choose a monster/source...")
    async def monster_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle monster selection."""
        try:
            monster = select.values[0]

            # Get items for this monster
            items = await self.bot.db_manager.get_items_by_monster(self.zone, monster)

            if not items:
                await interaction.response.send_message(
                    f"❌ No items configured for {monster}",
                    ephemeral=True
                )
                return

            # Show item selection
            view = ItemSelectView(self.bot, self.listing_type, self.zone, monster, items)

            embed = discord.Embed(
                title=f"🎯 Select Item",
                description=f"Choose an item from **{monster}**:",
                color=0x1E40AF
            )

            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in monster select: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass

class ItemSelectView(discord.ui.View):
    """View for selecting specific item."""

    def __init__(self, bot, listing_type: str, zone: str, monster: str, items: List[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone
        self.monster = monster

        # Create dropdown with items
        options = [
            discord.SelectOption(label=item, value=item)
            for item in items[:25]  # Discord limit of 25 options
        ]

        self.item_select.options = options

    @discord.ui.select(placeholder="Choose an item...")
    async def item_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle item selection."""
        try:
            item = select.values[0]

            # Check if this is a WTB listing and there are existing WTS listings for this item
            if self.listing_type.upper() == "WTB":
                sellers = await self.bot.db_manager.get_sellers_for_item(
                    interaction.guild.id, self.zone, item
                )

                if sellers:
                    # Show seller selection for joining queue
                    from bot.ui.modals import SellerJoinView
                    view = SellerJoinView(self.bot, sellers, self.zone, item)

                    embed = discord.Embed(
                        title="🔗 Sellers Found",
                        description=f"Some sellers are already offering **{item}**. Do you want to join their queue?",
                        color=0x3B82F6
                    )

                    await interaction.response.edit_message(embed=embed, view=view)
                    return

            # Create listing data for next step
            listing_data = {
                'listing_type': self.listing_type,
                'zone': self.zone,
                'subcategory': self.monster,
                'item': item
            }

            # Show quantity and notes modal
            from bot.ui.modals import QuantityNotesModal
            modal = QuantityNotesModal(self.bot, listing_data)

            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in item select: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass

class RemoveListingView(discord.ui.View):
    """View for removing user's listings."""

    def __init__(self, bot, listings: List[Dict[str, Any]], listing_type: str, zone: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone

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
            # Use direct database call instead of service to avoid circular imports
            success = await self.bot.db_manager.remove_listing(listing_id, interaction.user.id)

            if success:
                # Acknowledge the interaction first
                await interaction.response.send_message(
                    "✅ Listing removed successfully!",
                    ephemeral=True
                )

                # Then refresh the marketplace embed in the background
                asyncio.create_task(self.refresh_marketplace_embed(interaction))

            else:
                await interaction.response.send_message(
                    "❌ Could not remove listing. It may have already been removed.",
                    ephemeral=True
                )

        except discord.errors.NotFound:
            logger.error("Interaction expired while removing listing")
        except Exception as e:
            logger.error(f"Error removing listing: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while removing the listing",
                        ephemeral=True
                    )
            except:
                pass

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh the marketplace embed in the channel."""
        try:
            # Get the specific marketplace channel for this listing type and zone
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = $2 AND zone = $3",
                interaction.guild.id, self.listing_type, self.zone
            )

            if not channel_info:
                logger.warning(f"No marketplace channel found for {self.listing_type} in {self.zone}")
                return

            channel_data = channel_info[0]
            channel = interaction.guild.get_channel(channel_data['channel_id'])

            if not channel:
                logger.warning(f"Channel {channel_data['channel_id']} not found")
                return

            # Get updated listings
            view = MarketplaceView(self.bot, self.listing_type, self.zone, 0)
            listings = await view.get_listings_with_queues(interaction.guild.id)

            # Create updated embed
            embeds = MarketplaceEmbeds()
            embed = embeds.create_marketplace_embed(
                self.listing_type, self.zone, listings, 0  # Reset to first page
            )

            # Create new view
            new_view = MarketplaceView(self.bot, self.listing_type, self.zone, 0)

            # Try to find and update the marketplace message
            message_id = channel_data.get('message_id')
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed, view=new_view)
                    return
                except discord.NotFound:
                    logger.warning(f"Marketplace message {message_id} not found")

            # If message_id doesn't work, search for the message
            async for message in channel.history(limit=50):
                if (message.author == self.bot.user and 
                    message.embeds and 
                    message.embeds[0].title and 
                    self.listing_type.upper() in message.embeds[0].title and
                    self.zone.lower() in message.embeds[0].title.lower()):
                    await message.edit(embed=embed, view=new_view)

                    # Update the stored message_id
                    await self.bot.db_manager.execute_command(
                        "UPDATE marketplace_channels SET message_id = $1 WHERE channel_id = $2",
                        message.id, channel.id
                    )
                    break

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while refreshing the marketplace", ephemeral=True)


class EventConfirmationView(discord.ui.View):
    def __init__(self, listing_id, item_name):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.listing_id = listing_id
        self.item_name = item_name

    @discord.ui.button(label="✅ Confirm Participation", style=discord.ButtonStyle.green)
    async def confirm_participation(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            from bot.database.connection import execute_query

            # Record confirmation with 1-hour timer for rating
            rating_time = datetime.now(timezone.utc) + timedelta(hours=1)

            await execute_query("""
                INSERT INTO event_confirmations (listing_id, user_id, status, confirmed_at, rating_time, rating_sent)
                VALUES ($1, $2, 'confirmed', $3, $4, FALSE)
                ON CONFLICT (listing_id, user_id) DO UPDATE SET 
                status = 'confirmed', confirmed_at = $3, rating_time = $4
            """, self.listing_id, interaction.user.id, datetime.now(timezone.utc), rating_time)

            await interaction.response.send_message(f"✅ Participation confirmed for **{self.item_name}**. You'll receive a rating prompt in 1 hour.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error confirming participation: {e}")
            await interaction.response.send_message("❌ Error confirming participation.", ephemeral=True)


class RatingView(discord.ui.View):
    def __init__(self, listing_id, seller_id):
        super().__init__(timeout=3600)
        self.listing_id = listing_id
        self.seller_id = seller_id

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, custom_id="rating_1")
    async def rating_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit_rating(interaction, 1)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rating_2")
    async def rating_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit_rating(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rating_3")
    async def rating_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit_rating(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="rating_4")
    async def rating_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit_rating(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.primary, custom_id="rating_5")
    async def rating_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit_rating(interaction, 5)

    async def _submit_rating(self, interaction: discord.Interaction, rating: int):
        try:
            from bot.database.connection import execute_query

            # Save rating to seller's profile
            await execute_query("""
                INSERT INTO seller_ratings (seller_id, rater_id, listing_id, rating, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, self.seller_id, interaction.user.id, self.listing_id, rating, datetime.now(timezone.utc))

            await interaction.response.send_message(f"✅ Thank you for rating! You gave {rating} star{'s' if rating != 1 else ''}.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error submitting rating: {e}")
            await interaction.response.send_message("❌ Error submitting rating.", ephemeral=True)