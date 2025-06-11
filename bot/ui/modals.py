
import discord
from discord.ext import commands
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone, timedelta
import asyncio

logger = logging.getLogger(__name__)

class ListingModal(discord.ui.Modal, title="Create Listing"):
    """Modal for creating marketplace listings."""

    def __init__(self, bot, listing_type: str, zone: str):
        super().__init__()
        self.bot = bot
        self.listing_type = listing_type
        self.zone = zone

    subcategory = discord.ui.TextInput(
        label="Subcategory",
        placeholder="e.g., Kirin, Dynamis - Jeuno, etc.",
        required=True,
        max_length=100
    )

    item = discord.ui.TextInput(
        label="Item Name",
        placeholder="e.g., Shining Cloth, Hope Torque, etc.",
        required=True,
        max_length=200
    )

    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="1",
        required=False,
        max_length=10,
        default="1"
    )

    scheduled_time = discord.ui.TextInput(
        label="Scheduled Time (MM/DD - HH:MM)",
        placeholder="e.g., 06/15 - 20:00",
        required=False,
        max_length=50
    )

    notes = discord.ui.TextInput(
        label="Additional Notes",
        placeholder="Any additional information...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            # Parse quantity
            try:
                quantity_val = int(self.quantity.value) if self.quantity.value else 1
            except ValueError:
                quantity_val = 1

            # Parse scheduled time
            scheduled_datetime = None
            if self.scheduled_time.value:
                try:
                    # Parse MM/DD - HH:MM format
                    time_parts = self.scheduled_time.value.strip().split(' - ')
                    if len(time_parts) == 2:
                        date_part = time_parts[0].strip()
                        time_part = time_parts[1].strip()
                        
                        # Parse date (MM/DD)
                        month, day = map(int, date_part.split('/'))
                        
                        # Parse time (HH:MM)
                        hour, minute = map(int, time_part.split(':'))
                        
                        # Create datetime for current year
                        current_year = datetime.now().year
                        scheduled_datetime = datetime(current_year, month, day, hour, minute, tzinfo=timezone.utc)
                        
                        # If the date is in the past, assume next year
                        if scheduled_datetime < datetime.now(timezone.utc):
                            scheduled_datetime = scheduled_datetime.replace(year=current_year + 1)
                            
                except Exception as e:
                    logger.warning(f"Could not parse scheduled time '{self.scheduled_time.value}': {e}")

            # Create listing in database
            listing_id = await self.bot.db_manager.create_listing(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                listing_type=self.listing_type,
                zone=self.zone,
                subcategory=self.subcategory.value,
                item=self.item.value,
                quantity=quantity_val,
                notes=self.notes.value,
                scheduled_time=scheduled_datetime
            )

            if listing_id:
                # Create confirmation embed
                from bot.ui.embeds import MarketplaceEmbeds
                embeds = MarketplaceEmbeds()
                
                listing_data = {
                    'listing_type': self.listing_type,
                    'zone': self.zone,
                    'item': self.item.value,
                    'quantity': quantity_val,
                    'notes': self.notes.value,
                    'scheduled_time': scheduled_datetime
                }
                
                embed = embeds.create_listing_confirmation_embed(listing_data)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

                # Refresh marketplace embed
                asyncio.create_task(self.refresh_marketplace_embed(interaction))
            else:
                await interaction.response.send_message(
                    "❌ Failed to create listing. Please try again.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in listing modal submission: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while creating the listing",
                        ephemeral=True
                    )
            except:
                pass

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh the marketplace embed after creating a listing."""
        try:
            # Import here to avoid circular imports
            from bot.ui.views import MarketplaceView
            
            # Get the marketplace channel for this listing type and zone
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = $2 AND zone = $3",
                interaction.guild.id, self.listing_type, self.zone
            )

            if channel_info:
                channel_data = channel_info[0]
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                
                if channel:
                    # Get updated listings
                    view = MarketplaceView(self.bot, self.listing_type, self.zone, 0)
                    listings = await view.get_listings_with_queues(interaction.guild.id)

                    # Create updated embed
                    from bot.ui.embeds import MarketplaceEmbeds
                    embeds = MarketplaceEmbeds()
                    embed = embeds.create_marketplace_embed(
                        self.listing_type, self.zone, listings, 0
                    )

                    # Create new view
                    new_view = MarketplaceView(self.bot, self.listing_type, self.zone, 0)

                    # Update the message
                    message_id = channel_data.get('message_id')
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed, view=new_view)
                        except discord.NotFound:
                            logger.warning(f"Message {message_id} not found")

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class QuantityNotesModal(discord.ui.Modal, title="Listing Details"):
    """Modal for quantity, notes, and scheduling."""

    def __init__(self, bot, listing_data: Dict[str, Any]):
        super().__init__()
        self.bot = bot
        self.listing_data = listing_data

        # Only show scheduled time for WTS listings
        if listing_data['listing_type'].upper() == 'WTS':
            self.scheduled_time = discord.ui.TextInput(
                label="Scheduled Time (MM/DD - HH:MM)",
                placeholder="e.g., 06/15 - 20:00",
                required=False,
                max_length=50
            )
            self.add_item(self.scheduled_time)

    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="1",
        required=False,
        max_length=10,
        default="1"
    )

    notes = discord.ui.TextInput(
        label="Additional Notes",
        placeholder="Any additional information...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            # Parse quantity
            try:
                quantity_val = int(self.quantity.value) if self.quantity.value else 1
            except ValueError:
                quantity_val = 1

            # Parse scheduled time (only for WTS)
            scheduled_datetime = None
            if (self.listing_data['listing_type'].upper() == 'WTS' and 
                hasattr(self, 'scheduled_time') and self.scheduled_time.value):
                try:
                    # Parse MM/DD - HH:MM format
                    time_parts = self.scheduled_time.value.strip().split(' - ')
                    if len(time_parts) == 2:
                        date_part = time_parts[0].strip()
                        time_part = time_parts[1].strip()
                        
                        # Parse date (MM/DD)
                        month, day = map(int, date_part.split('/'))
                        
                        # Parse time (HH:MM)
                        hour, minute = map(int, time_part.split(':'))
                        
                        # Create datetime for current year
                        current_year = datetime.now().year
                        scheduled_datetime = datetime(current_year, month, day, hour, minute, tzinfo=timezone.utc)
                        
                        # If the date is in the past, assume next year
                        if scheduled_datetime < datetime.now(timezone.utc):
                            scheduled_datetime = scheduled_datetime.replace(year=current_year + 1)
                            
                except Exception as e:
                    logger.warning(f"Could not parse scheduled time: {e}")

            # Create listing in database
            listing_id = await self.bot.db_manager.create_listing(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                listing_type=self.listing_data['listing_type'],
                zone=self.listing_data['zone'],
                subcategory=self.listing_data['subcategory'],
                item=self.listing_data['item'],
                quantity=quantity_val,
                notes=self.notes.value,
                scheduled_time=scheduled_datetime
            )

            if listing_id:
                # Create confirmation embed
                from bot.ui.embeds import MarketplaceEmbeds
                embeds = MarketplaceEmbeds()
                
                listing_data = {
                    **self.listing_data,
                    'quantity': quantity_val,
                    'notes': self.notes.value,
                    'scheduled_time': scheduled_datetime
                }
                
                embed = embeds.create_listing_confirmation_embed(listing_data)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

                # Refresh marketplace embed
                asyncio.create_task(self.refresh_marketplace_embed(interaction))
            else:
                await interaction.response.send_message(
                    "❌ Failed to create listing. Please try again.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in quantity/notes modal submission: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while creating the listing",
                        ephemeral=True
                    )
            except:
                pass

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh the marketplace embed after creating a listing."""
        try:
            # Import here to avoid circular imports
            from bot.ui.views import MarketplaceView
            
            # Get the marketplace channel for this listing type and zone
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = $2 AND zone = $3",
                interaction.guild.id, self.listing_data['listing_type'], self.listing_data['zone']
            )

            if channel_info:
                channel_data = channel_info[0]
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                
                if channel:
                    # Get updated listings with queue data
                    view = MarketplaceView(self.bot, self.listing_data['listing_type'], self.listing_data['zone'], 0)
                    listings = await view.get_listings_with_queues(interaction.guild.id)

                    # Create updated embed
                    from bot.ui.embeds import MarketplaceEmbeds
                    embeds = MarketplaceEmbeds()
                    embed = embeds.create_marketplace_embed(
                        self.listing_data['listing_type'], self.listing_data['zone'], listings, 0
                    )

                    # Create new view
                    new_view = MarketplaceView(self.bot, self.listing_data['listing_type'], self.listing_data['zone'], 0)

                    # Update the message
                    message_id = channel_data.get('message_id')
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed, view=new_view)
                        except discord.NotFound:
                            logger.warning(f"Message {message_id} not found")

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class QueueSelectView(discord.ui.View):
    """View for selecting items to queue for."""

    def __init__(self, bot, wts_listings: List[Dict[str, Any]], zone: str, available_items: List[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.wts_listings = wts_listings
        self.zone = zone

        # Create dropdown with available items (max 25)
        options = []
        for item in available_items[:25]:
            options.append(discord.SelectOption(label=item, value=item))

        self.item_select.options = options

    @discord.ui.select(placeholder="Select an item to queue for...")
    async def item_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle item selection for queue."""
        try:
            item_name = select.values[0]

            # Find sellers offering this item
            sellers = await self.bot.db_manager.get_sellers_for_item(
                interaction.guild.id, self.zone, item_name
            )

            if not sellers:
                await interaction.response.send_message(
                    f"❌ No sellers currently offering **{item_name}** in {self.zone.title()}.",
                    ephemeral=True
                )
                return

            # If only one seller, add directly to queue
            if len(sellers) == 1:
                seller = sellers[0]
                success = await self.bot.db_manager.add_to_queue(
                    seller['id'], interaction.user.id, item_name
                )

                if success:
                    await interaction.response.send_message(
                        f"✅ You have been added to the queue for **{item_name}** by <@{seller['user_id']}>",
                        ephemeral=True
                    )
                    # Refresh the marketplace embed
                    asyncio.create_task(self.refresh_marketplace_embed(interaction))
                else:
                    await interaction.response.send_message(
                        f"❌ Could not add you to the queue. You may already be queued for this item or you are the seller.",
                        ephemeral=True
                    )
            else:
                # Multiple sellers, show selection
                view = SellerSelectView(self.bot, sellers, self.zone, item_name)
                
                embed = discord.Embed(
                    title="👥 Select Seller",
                    description=f"Multiple sellers are offering **{item_name}**. Choose one:",
                    color=0x3B82F6
                )

                await interaction.response.edit_message(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in queue item selection: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while joining the queue",
                        ephemeral=True
                    )
            except:
                pass

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh marketplace embed after queue change."""
        try:
            from bot.ui.views import MarketplaceView
            
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = 'WTS' AND zone = $2",
                interaction.guild.id, self.zone
            )

            if channel_info:
                channel_data = channel_info[0]
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                
                if channel:
                    view = MarketplaceView(self.bot, 'WTS', self.zone, 0)
                    listings = await view.get_listings_with_queues(interaction.guild.id)

                    from bot.ui.embeds import MarketplaceEmbeds
                    embeds = MarketplaceEmbeds()
                    embed = embeds.create_marketplace_embed('WTS', self.zone, listings, 0)
                    new_view = MarketplaceView(self.bot, 'WTS', self.zone, 0)

                    message_id = channel_data.get('message_id')
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed, view=new_view)
                        except discord.NotFound:
                            pass

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class SellerSelectView(discord.ui.View):
    """View for selecting which seller to queue with."""

    def __init__(self, bot, sellers: List[Dict[str, Any]], zone: str, item_name: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.zone = zone
        self.item_name = item_name

        # Create dropdown with sellers
        options = []
        for seller in sellers[:25]:  # Discord limit
            scheduled_time = seller.get('scheduled_time')
            time_str = "No time set"
            if scheduled_time:
                timestamp = int(scheduled_time.timestamp())
                time_str = f"<t:{timestamp}:R>"
            
            label = f"Seller: {seller.get('username', 'Unknown')} - {time_str}"
            if len(label) > 100:
                label = label[:97] + "..."
                
            options.append(discord.SelectOption(
                label=label,
                value=str(seller['id']),
                description=seller.get('notes', '')[:100] if seller.get('notes') else None
            ))

        self.seller_select.options = options

    @discord.ui.select(placeholder="Select a seller to queue with...")
    async def seller_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle seller selection for queue."""
        try:
            listing_id = int(select.values[0])

            success = await self.bot.db_manager.add_to_queue(
                listing_id, interaction.user.id, self.item_name
            )

            if success:
                # Get seller info
                seller_info = await self.bot.db_manager.execute_query(
                    "SELECT user_id FROM listings WHERE id = $1",
                    listing_id
                )
                
                if seller_info:
                    seller_id = seller_info[0]['user_id']
                    await interaction.response.send_message(
                        f"✅ You have been added to the queue for **{self.item_name}** by <@{seller_id}>",
                        ephemeral=True
                    )
                    # Refresh the marketplace embed
                    asyncio.create_task(self.refresh_marketplace_embed(interaction))
                else:
                    await interaction.response.send_message(
                        "✅ You have been added to the queue!",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "❌ Could not add you to the queue. You may already be queued for this item or you are the seller.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in seller selection: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while joining the queue",
                        ephemeral=True
                    )
            except:
                pass

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh marketplace embed after queue change."""
        try:
            from bot.ui.views import MarketplaceView
            
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = 'WTS' AND zone = $2",
                interaction.guild.id, self.zone
            )

            if channel_info:
                channel_data = channel_info[0]
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                
                if channel:
                    view = MarketplaceView(self.bot, 'WTS', self.zone, 0)
                    listings = await view.get_listings_with_queues(interaction.guild.id)

                    from bot.ui.embeds import MarketplaceEmbeds
                    embeds = MarketplaceEmbeds()
                    embed = embeds.create_marketplace_embed('WTS', self.zone, listings, 0)
                    new_view = MarketplaceView(self.bot, 'WTS', self.zone, 0)

                    message_id = channel_data.get('message_id')
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed, view=new_view)
                        except discord.NotFound:
                            pass

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class SellerJoinView(discord.ui.View):
    """View for WTB buyers to join existing WTS seller queues."""

    def __init__(self, bot, sellers: List[Dict[str, Any]], zone: str, item_name: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.zone = zone
        self.item_name = item_name

        # Create dropdown with sellers
        options = []
        for seller in sellers[:25]:  # Discord limit
            scheduled_time = seller.get('scheduled_time')
            time_str = "No time set"
            if scheduled_time:
                timestamp = int(scheduled_time.timestamp())
                time_str = f"<t:{timestamp}:R>"
            
            label = f"Join queue: {seller.get('username', 'Unknown')} - {time_str}"
            if len(label) > 100:
                label = label[:97] + "..."
                
            options.append(discord.SelectOption(
                label=label,
                value=str(seller['id']),
                description=seller.get('notes', '')[:100] if seller.get('notes') else None
            ))

        self.seller_select.options = options

    @discord.ui.select(placeholder="Select a seller to join their queue...")
    async def seller_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle seller selection for joining queue."""
        try:
            listing_id = int(select.values[0])

            success = await self.bot.db_manager.add_to_queue(
                listing_id, interaction.user.id, self.item_name
            )

            if success:
                # Get seller info
                seller_info = await self.bot.db_manager.execute_query(
                    "SELECT user_id FROM listings WHERE id = $1",
                    listing_id
                )
                
                if seller_info:
                    seller_id = seller_info[0]['user_id']
                    await interaction.response.send_message(
                        f"✅ You have been added to <@{seller_id}>'s queue for **{self.item_name}**!",
                        ephemeral=True
                    )
                    # Refresh the marketplace embed
                    asyncio.create_task(self.refresh_marketplace_embed(interaction))
                else:
                    await interaction.response.send_message(
                        "✅ You have been added to the queue!",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "❌ Could not add you to the queue. You may already be queued for this item.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in seller join selection: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while joining the queue",
                        ephemeral=True
                    )
            except:
                pass

    @discord.ui.button(label="Create My Own Listing", style=discord.ButtonStyle.secondary)
    async def create_own_listing(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Allow user to create their own WTB listing instead."""
        try:
            # Create listing data for WTB
            listing_data = {
                'listing_type': 'WTB',
                'zone': self.zone,
                'subcategory': 'Wanted',
                'item': self.item_name
            }

            # Show quantity and notes modal (no scheduling for WTB)
            modal = QuantityNotesModal(self.bot, listing_data)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error creating own listing: {e}")

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh marketplace embed after queue change."""
        try:
            from bot.ui.views import MarketplaceView
            
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = 'WTS' AND zone = $2",
                interaction.guild.id, self.zone
            )

            if channel_info:
                channel_data = channel_info[0]
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                
                if channel:
                    view = MarketplaceView(self.bot, 'WTS', self.zone, 0)
                    listings = await view.get_listings_with_queues(interaction.guild.id)

                    from bot.ui.embeds import MarketplaceEmbeds
                    embeds = MarketplaceEmbeds()
                    embed = embeds.create_marketplace_embed('WTS', self.zone, listings, 0)
                    new_view = MarketplaceView(self.bot, 'WTS', self.zone, 0)

                    message_id = channel_data.get('message_id')
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed, view=new_view)
                        except discord.NotFound:
                            pass

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class LeaveQueueView(discord.ui.View):
    """View for leaving queues."""

    def __init__(self, bot, user_queues: List[Dict[str, Any]], zone: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.zone = zone

        # Create dropdown with user's queue entries
        options = []
        for queue in user_queues[:25]:  # Discord limit
            label = f"Leave queue for: {queue['item_name']}"
            if len(label) > 100:
                label = label[:97] + "..."
                
            options.append(discord.SelectOption(
                label=label,
                value=f"{queue['listing_id']}|{queue['item_name']}",
                description=f"Seller: User {queue['seller_id']}"
            ))

        self.queue_select.options = options

    @discord.ui.select(placeholder="Select a queue to leave...")
    async def queue_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle queue leave selection."""
        try:
            value_parts = select.values[0].split('|')
            listing_id = int(value_parts[0])
            item_name = value_parts[1]

            success = await self.bot.db_manager.remove_from_queue_by_item(
                interaction.user.id, listing_id, item_name
            )

            if success:
                await interaction.response.send_message(
                    f"✅ You have left the queue for **{item_name}**",
                    ephemeral=True
                )
                # Refresh the marketplace embed
                asyncio.create_task(self.refresh_marketplace_embed(interaction))
            else:
                await interaction.response.send_message(
                    "❌ Could not remove you from the queue.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error leaving queue: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while leaving the queue",
                        ephemeral=True
                    )
            except:
                pass

    async def refresh_marketplace_embed(self, interaction: discord.Interaction):
        """Refresh marketplace embed after queue change."""
        try:
            from bot.ui.views import MarketplaceView
            
            channel_info = await self.bot.db_manager.execute_query(
                "SELECT channel_id, message_id FROM marketplace_channels WHERE guild_id = $1 AND listing_type = 'WTS' AND zone = $2",
                interaction.guild.id, self.zone
            )

            if channel_info:
                channel_data = channel_info[0]
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                
                if channel:
                    view = MarketplaceView(self.bot, 'WTS', self.zone, 0)
                    listings = await view.get_listings_with_queues(interaction.guild.id)

                    from bot.ui.embeds import MarketplaceEmbeds
                    embeds = MarketplaceEmbeds()
                    embed = embeds.create_marketplace_embed('WTS', self.zone, listings, 0)
                    new_view = MarketplaceView(self.bot, 'WTS', self.zone, 0)

                    message_id = channel_data.get('message_id')
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.edit(embed=embed, view=new_view)
                        except discord.NotFound:
                            pass

        except Exception as e:
            logger.error(f"Error refreshing marketplace embed: {e}")

class QueueSearchModal(discord.ui.Modal, title="Search Items"):
    """Modal for searching items when there are too many for a dropdown."""

    def __init__(self, bot, zone: str):
        super().__init__()
        self.bot = bot
        self.zone = zone

    search_term = discord.ui.TextInput(
        label="Search for an item",
        placeholder="Enter item name to search...",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission."""
        try:
            search_results = await self.bot.db_manager.search_items(
                self.zone, self.search_term.value
            )

            if not search_results:
                await interaction.response.send_message(
                    f"❌ No items found matching '{self.search_term.value}' in {self.zone.title()}",
                    ephemeral=True
                )
                return

            # Show search results
            items = [result['item_name'] for result in search_results]
            view = QueueSelectView(self.bot, [], self.zone, items)
            
            embed = discord.Embed(
                title="🔍 Search Results",
                description=f"Found {len(items)} item(s) matching '{self.search_term.value}':",
                color=0x00FF00
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in search modal: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while searching",
                        ephemeral=True
                    )
            except:
                pass
