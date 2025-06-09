"""
Main bot client class with event handlers and command registration.
"""

import logging
import discord
from discord.ext import commands, tasks
from typing import Optional

from bot.database.connection import DatabaseManager
from bot.database.migrations import run_migrations
from bot.commands.marketplace import MarketplaceCommands
from bot.services.scheduler import ExpiryScheduler
from config.settings import COMMAND_PREFIX, INTENTS

logger = logging.getLogger(__name__)

class MandokBot(commands.Bot):
    """Main bot class for Mandok marketplace bot."""
    
    def __init__(self):
        super().__init__(
            command_prefix=COMMAND_PREFIX,
            intents=INTENTS,
            help_command=None
        )
        
        self.db_manager: Optional[DatabaseManager] = None
        self.scheduler: Optional[ExpiryScheduler] = None
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")
        
        # Initialize database
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        
        # Run database migrations
        await run_migrations(self.db_manager)
        
        # Initialize scheduler
        self.scheduler = ExpiryScheduler(self)
        
        # Add command cogs
        await self.add_cog(MarketplaceCommands(self))
        
        # Start background tasks
        self.expiry_check.start()
        
        logger.info("Bot setup complete")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Load persistent views for all marketplace channels
        await self.load_persistent_views()
        
        # Sync application commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def load_persistent_views(self):
        """Load persistent views for marketplace channels."""
        try:
            from bot.ui.views import MarketplaceView
            
            # Get all marketplace channels from database
            marketplace_channels = await self.db_manager.execute_query("""
                SELECT channel_id, listing_type, zone FROM marketplace_channels
            """)
            
            for channel_data in marketplace_channels:
                channel_id = channel_data['channel_id']
                listing_type = channel_data['listing_type']
                zone = channel_data['zone']
                
                # Validate zone data before creating view
                if zone and zone != "unknown":
                    # Create and add persistent view
                    view = MarketplaceView(self, listing_type, zone)
                    self.add_view(view)
                else:
                    logger.warning(f"Skipping invalid zone '{zone}' for channel {channel_id}")
                
            logger.info(f"Loaded {len(marketplace_channels)} persistent marketplace views")
            
        except Exception as e:
            logger.error(f"Error loading persistent views: {e}")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
        # Clean up guild data
        if self.db_manager:
            await self.db_manager.cleanup_guild_data(guild.id)
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Global error handler."""
        logger.error(f"Error in {event_method}", exc_info=True)
    
    @tasks.loop(minutes=5)
    async def expiry_check(self):
        """Check for expired listings every 5 minutes."""
        if self.scheduler:
            try:
                await self.scheduler.check_expired_listings()
            except Exception as e:
                logger.error(f"Error in expiry check: {e}")
    
    @expiry_check.before_loop
    async def before_expiry_check(self):
        """Wait until bot is ready before starting expiry checks."""
        await self.wait_until_ready()
    
    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("Shutting down bot...")
        
        # Stop background tasks
        if self.expiry_check.is_running():
            self.expiry_check.stop()
        
        # Close database connection
        if self.db_manager:
            await self.db_manager.close()
        
        await super().close()
        logger.info("Bot shutdown complete")
