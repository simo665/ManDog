import asyncio
import logging
import os
from dotenv import load_dotenv

from bot.client import MandokBot
from bot.utils.logger import setup_logging
from config.settings import BOT_TOKEN, DATABASE_URL
import traceback

def main():
    """Main entry point for the bot."""
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Validate required environment variables
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return

    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        return

    logger.info("Starting Mandok Discord Bot...")

    # Create and run the bot
    bot = MandokBot()
    
    try:
        async def run_bot():
            # Call setup_hook to initialize db_manager
            await bot.setup_hook() 

            # Initialize scheduler service
            from bot.services.scheduler import SchedulerService
            bot.scheduler = SchedulerService(bot)
            await bot.scheduler.start()

            # Start the bot
            logger.info("Starting Mandok Bot...")
            await bot.start(BOT_TOKEN)

        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {traceback.format_exc()}")
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()