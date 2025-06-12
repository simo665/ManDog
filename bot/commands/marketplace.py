import logging
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timezone

from bot.ui.embeds import MarketplaceEmbeds
from bot.ui.views import SetupView, MarketplaceView
from bot.ui.modals import TimezoneModal
from bot.utils.permissions import is_admin
from config.settings import BOT_OWNERS

logger = logging.getLogger(__name__)

class MarketplaceCommands(commands.Cog):
    """Marketplace command handlers."""

    def __init__(self, bot):
        self.bot = bot
        self.embeds = MarketplaceEmbeds()

    @app_commands.command(name="marketplace", description="Initialize the marketplace system")
    @app_commands.describe(setup="Set up marketplace categories and channels")
    async def marketplace(self, interaction: discord.Interaction, setup: bool):
        """Main marketplace command."""

        # Check if user is admin
        if not is_admin(interaction.user, interaction.guild):
            await interaction.response.send_message(
                "❌ You must be an administrator to use this command.",
                ephemeral=True
            )
            return

        try:
            if setup:
                # Send setup panel
                embed = self.embeds.create_setup_embed()
                view = SetupView(self.bot)

                await interaction.response.send_message(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
            else:
                # Send admin panel
                embed = self.embeds.create_admin_embed()

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in marketplace command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing the command.",
                ephemeral=True
            )

    async def setup_marketplace_channels(self, guild: discord.Guild, interaction: discord.Interaction):
        """Set up marketplace categories and channels."""
        try:
            # Clean up any invalid channel data before setup
            await self.cleanup_invalid_channels(guild)

            # Check if already set up
            existing_config = await self.bot.db_manager.execute_query(
                "SELECT setup_complete FROM guild_configs WHERE guild_id = $1",
                guild.id
            )

            # Categories to create
            categories_data = [
                ("WTS - Sellers", "🔸"),
                ("WTB - Buyers", "🔹")
            ]

            # Channels for each category
            channel_names = ["sky", "sea", "dynamis", "limbus", "others"]

            created_channels = []

            # Get current guild categories and channels
            guild_categories = {category.name: category for category in guild.categories}
            guild_channels = {channel.name: channel for channel in guild.channels}

            for category_name, emoji in categories_data:
                # Create or get existing category
                category = None
                if category_name not in guild_categories:
                    category = await guild.create_category(
                        name=category_name,
                        reason="Marketplace setup by Mandok bot"
                    )
                    logger.info(f"Created category: {category_name}")
                else:
                    category = guild_categories[category_name]
                    logger.info(f"Using existing category: {category_name}")
                if not category:
                    logger.error(f"Failed to create/get category: {category_name}")
                    continue 

                # Create channels in category
                for channel_name in channel_names:
                    name_with_emoji = f"{emoji}{channel_name}"

                    # Check if channel exists and handle it
                    existing_channel = guild_channels.get(name_with_emoji)
                    if existing_channel:
                        try:
                            # Verify the channel actually exists and is accessible
                            await existing_channel.fetch_message(existing_channel.last_message_id or 0)
                        except (discord.NotFound, discord.Forbidden, AttributeError):
                            # Channel exists but we can't access it properly, or it's in a bad state
                            logger.warning(f"Channel {name_with_emoji} exists but is inaccessible, recreating...")
                            try:
                                await existing_channel.delete(reason="Recreating marketplace channel")
                                logger.info(f"Deleted existing channel: {name_with_emoji}")
                            except discord.NotFound:
                                # Channel was already deleted
                                logger.info(f"Channel {name_with_emoji} was already deleted")
                            except Exception as e:
                                logger.error(f"Failed to delete existing channel {name_with_emoji}: {e}")
                        else:
                            # Channel exists and is accessible, delete it to recreate
                            try:
                                await existing_channel.delete(reason="Recreating marketplace channel")
                                logger.info(f"Deleted existing channel: {name_with_emoji}")
                            except Exception as e:
                                logger.error(f"Failed to delete existing channel {name_with_emoji}: {e}")
                                continue

                    # Create new channel
                    try:
                        channel = await guild.create_text_channel(
                            name=name_with_emoji,
                            category=category,
                            topic=f"Marketplace for {channel_name} content",
                            reason="Marketplace setup by Mandok bot"
                        )
                        logger.info(f"Created channel: {name_with_emoji}")
                    except Exception as e:
                        logger.error(f"Failed to create channel {name_with_emoji}: {e}")
                        continue

                    if not channel:
                        logger.error(f"Channel creation returned None for: {name_with_emoji}")
                        continue

                    # Set channel permissions (read-only for @everyone)
                    try:
                        await channel.set_permissions(
                            guild.default_role,
                            send_messages=False,
                            add_reactions=False
                        )
                        logger.info(f"Set permissions for channel: {name_with_emoji}")
                    except Exception as e:
                        logger.error(f"Failed to set permissions for {name_with_emoji}: {e}")

                    # Create persistent embed and view
                    try:
                        # Extract proper listing type from category name
                        listing_type = "WTS" if "WTS" in category_name else "WTB"
                        await self.setup_channel_embed(channel, listing_type, channel_name)
                        created_channels.append(channel)
                        logger.info(f"Set up embed for channel: {name_with_emoji}")
                    except Exception as e:
                        logger.error(f"Failed to setup embed for {name_with_emoji}: {e}")

            # Store setup data in database
            await self.bot.db_manager.store_guild_setup(guild.id, created_channels)

            # Update interaction with success message
            success_embed = self.embeds.create_setup_success_embed(len(created_channels))
            await interaction.edit_original_response(embed=success_embed, view=None)

            logger.info(f"Marketplace setup completed for guild {guild.name} ({guild.id}) - {len(created_channels)} channels created")

        except Exception as e:
            logger.error(f"Error setting up marketplace: {e}")
            error_embed = self.embeds.create_error_embed("Failed to set up marketplace channels")
            try:
                await interaction.edit_original_response(embed=error_embed, view=None)
            except Exception as edit_error:
                logger.error(f"Failed to edit interaction response: {edit_error}")

    @app_commands.command(name="settimezone", description="Set your timezone for scheduling")
    async def set_timezone(self, interaction: discord.Interaction):
        """Set user timezone."""
        try:
            modal = TimezoneModal(self.bot)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in set timezone command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while opening timezone setup.",
                ephemeral=True
            )

    @app_commands.command(name="items", description="Admin command to manage items")
    @app_commands.describe(
        action="Action to perform",
        zone="Zone name",
        monster_name="Monster name",
        item_name="Item name"
    )
    async def items_command(
        self, 
        interaction: discord.Interaction,
        action: str,
        zone: str = None,
        monster_name: str = None,
        item_name: str = None
    ):
        """Admin command for managing items."""
        try:
            # Check if user is bot owner
            if interaction.user.id not in BOT_OWNERS:
                await interaction.response.send_message(
                    "❌ This command is restricted to bot owners only.",
                    ephemeral=True
                )
                return

            if action.lower() == "add":
                if not all([zone, monster_name, item_name]):
                    await interaction.response.send_message(
                        "❌ Usage: `/items add <zone> <monster_name> <item_name>`",
                        ephemeral=True
                    )
                    return

                # Add item to database
                success = await self.bot.db_manager.add_item(
                    zone.lower(), monster_name, item_name, interaction.user.id
                )

                if success:
                    embed = discord.Embed(
                        title="✅ Item Added",
                        description=f"Successfully added **{item_name}** from **{monster_name}** in **{zone}**",
                        color=0x00FF00
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        "❌ Failed to add item. It may already exist.",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "❌ Valid actions: `add`",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in items command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while managing items.",
                ephemeral=True
            )t_error}")

    async def cleanup_invalid_channels(self, guild: discord.Guild):
        """Clean up database entries for channels that no longer exist."""
        try:
            # First, remove ALL existing marketplace channel data for this guild to prevent duplicates
            await self.bot.db_manager.execute_command(
                "DELETE FROM marketplace_channels WHERE guild_id = $1",
                guild.id
            )
            logger.info(f"Cleared all existing marketplace channel data for guild {guild.id}")

            # Get all stored channels for this guild (should be empty now)
            stored_channels = await self.bot.db_manager.execute_query(
                "SELECT channel_id, listing_type, zone FROM marketplace_channels WHERE guild_id = $1",
                guild.id
            )

            if not stored_channels:
                logger.info(f"No stored channels found for guild {guild.id} after cleanup")
                return

            # Check which channels still exist
            guild_channel_ids = {channel.id for channel in guild.channels}
            channels_to_remove = []

            for channel_data in stored_channels:
                channel_id = channel_data['channel_id']
                if channel_id not in guild_channel_ids:
                    channels_to_remove.append(channel_id)
                    logger.info(f"Found orphaned channel data for channel_id: {channel_id}")

            # Remove invalid channel data
            if channels_to_remove:
                await self.bot.db_manager.cleanup_invalid_channels(channels_to_remove)
                logger.info(f"Cleaned up {len(channels_to_remove)} invalid channel entries for guild {guild.id}")

        except Exception as e:
            logger.error(f"Error cleaning up invalid channels for guild {guild.id}: {e}")

    async def setup_channel_embed(self, channel: discord.TextChannel, listing_type: str, zone: str):
        """Set up persistent embed and buttons for a marketplace channel."""
        try:
            # Get existing listings for this zone and type
            existing_listings = await self.bot.db_manager.get_zone_listings(
                channel.guild.id, listing_type, zone
            )

            # Create embed for the channel with existing listings
            embed = self.embeds.create_marketplace_embed(listing_type, zone, existing_listings, 0)

            # Create view with appropriate buttons
            view = MarketplaceView(self.bot, listing_type, zone, 0)

            # Send the persistent message
            message = await channel.send(embed=embed, view=view)

            # Store message ID for later updates
            await self.bot.db_manager.store_marketplace_message(
                channel.guild.id,
                channel.id,
                message.id,
                listing_type,
                zone
            )

            logger.info(f"Created persistent message {message.id} in channel {channel.name} with {len(existing_listings)} existing listings")

        except Exception as e:
            logger.error(f"Error setting up channel embed for {channel.name}: {e}")
            raise

    @discord.app_commands.command(name="cleanup", description="Clean up expired listings")
    async def cleanup_listings(self, interaction: discord.Interaction):
        """Manually clean up expired listings."""
        try:
            if not is_admin(interaction.user, interaction.guild):
                await interaction.response.send_message(
                    "❌ You need admin permissions to use this command.", ephemeral=True
                )
                return

            # Clean up expired listings
            expired_count = await self.bot.db_manager.cleanup_expired_listings()

            await interaction.response.send_message(
                f"🧹 Cleaned up {expired_count} expired listings.", ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error cleaning up listings: {e}")
            await interaction.response.send_message(
                "An error occurred while cleaning up listings.", ephemeral=True
            )

    @discord.app_commands.command(name="setratingconfig", description="Configure rating moderation settings")
    @discord.app_commands.describe(
        admin_channel="Channel where low rating disputes will be sent for admin review",
        threshold="Ratings below this value will require admin approval (default: 3)"
    )
    async def set_rating_config(self, interaction: discord.Interaction, 
                              admin_channel: discord.TextChannel, 
                              threshold: int = 3):
        """Configure rating moderation settings."""
        try:
            if not is_admin(interaction.user, interaction.guild):
                await interaction.response.send_message(
                    "❌ You need admin permissions to use this command.", ephemeral=True
                )
                return

            if threshold < 1 or threshold > 5:
                await interaction.response.send_message(
                    "❌ Threshold must be between 1 and 5.", ephemeral=True
                )
                return

            # Store rating configuration
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO guild_rating_configs (guild_id, admin_channel_id, low_rating_threshold, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id)
                DO UPDATE SET 
                    admin_channel_id = $2,
                    low_rating_threshold = $3,
                    updated_at = $4
                """,
                interaction.guild.id, admin_channel.id, threshold, datetime.now(timezone.utc)
            )

            await interaction.response.send_message(
                f"✅ Rating configuration updated!\n"
                f"📝 Admin Channel: {admin_channel.mention}\n"
                f"⚠️ Low Rating Threshold: {threshold}/5 stars\n"
                f"Ratings below {threshold} stars will be sent to {admin_channel.mention} for admin review.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error setting rating config: {e}")
            await interaction.response.send_message(
                "An error occurred while setting rating configuration.", ephemeral=True
            )

def setup(bot):
    bot.add_cog(MarketplaceCommands(bot))