"""
Marketplace commands for the bot.
"""

import logging
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from bot.ui.embeds import MarketplaceEmbeds
from bot.ui.views import SetupView, MarketplaceView
from bot.utils.permissions import is_admin

logger = logging.getLogger(__name__)

class MarketplaceCommands(commands.Cog):
    """Marketplace command handlers."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = MarketplaceEmbeds()
    
    @app_commands.command(name="marketplace", description="Initialize the marketplace system")
    @app_commands.describe(setup="Set up marketplace categories and channels")
    async def marketplace(self, interaction: discord.Interaction, setup: bool = False):
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
            # Check if already set up
            existing_config = await self.bot.db_manager.execute_query(
                "SELECT setup_complete FROM guild_configs WHERE guild_id = $1",
                guild.id
            )
            
            if existing_config and existing_config[0]['setup_complete']:
                await interaction.followup.send(
                    "✅ Marketplace is already set up for this server!",
                    ephemeral=True
                )
                return
            
            # Categories to create
            categories_data = [
                ("WTS - Sellers", "🔸"),
                ("WTB - Buyers", "🔹")
            ]
            
            # Channels for each category
            channel_names = ["sky", "sea", "dynamis", "limbus", "others"]
            
            created_channels = []
            
            for category_name, emoji in categories_data:
                # Create category
                category = await guild.create_category(
                    name=category_name,
                    reason="Marketplace setup by Mandok bot"
                )
                
                # Create channels in category
                for channel_name in channel_names:
                    channel = await guild.create_text_channel(
                        name=f"{emoji}-{channel_name}",
                        category=category,
                        topic=f"Marketplace for {channel_name} content",
                        reason="Marketplace setup by Mandok bot"
                    )
                    
                    # Set channel permissions (read-only for @everyone)
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=False,
                        add_reactions=False
                    )
                    
                    # Create persistent embed and view
                    await self.setup_channel_embed(channel, category_name.split()[0], channel_name)
                    created_channels.append(channel)
            
            # Store setup data in database
            await self.bot.db_manager.store_guild_setup(guild.id, created_channels)
            
            # Update interaction with success message
            success_embed = self.embeds.create_setup_success_embed(len(created_channels))
            await interaction.edit_original_response(embed=success_embed, view=None)
            
            logger.info(f"Marketplace setup completed for guild {guild.name} ({guild.id})")
            
        except Exception as e:
            logger.error(f"Error setting up marketplace: {e}")
            error_embed = self.embeds.create_error_embed("Failed to set up marketplace channels")
            await interaction.edit_original_response(embed=error_embed, view=None)
    
    async def setup_channel_embed(self, channel: discord.TextChannel, listing_type: str, zone: str):
        """Set up persistent embed and buttons for a marketplace channel."""
        try:
            # Create embed for the channel with pagination
            embed = self.embeds.create_marketplace_embed(listing_type, zone, [], 0)
            
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
            
        except Exception as e:
            logger.error(f"Error setting up channel embed for {channel.name}: {e}")
