"""
Logging configuration and utilities.
"""

import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(level: str = "INFO", log_file: str = None):
    """Set up logging configuration."""

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Set up log level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file is None:
        log_file = f"logs/mandok_{datetime.now().strftime('%Y%m%d')}.log"

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Set specific logger levels
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {level}")
    logger.info(f"Log file: {log_file}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)

class ContextLogger:
    """Logger with context information."""

    def __init__(self, logger: logging.Logger, context: dict = None):
        self.logger = logger
        self.context = context or {}

    def _format_message(self, message: str) -> str:
        """Format message with context."""
        if self.context:
            context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"{message} | {context_str}"
        return message

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message), **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message), **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message), **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message), **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with context."""
        self.logger.exception(self._format_message(message), **kwargs)

def create_guild_logger(guild_id: int) -> ContextLogger:
    """Create a logger with guild context."""
    logger = logging.getLogger("mandok.guild")
    return ContextLogger(logger, {"guild_id": guild_id})

def create_user_logger(user_id: int) -> ContextLogger:
    """Create a logger with user context."""
    logger = logging.getLogger("mandok.user")
    return ContextLogger(logger, {"user_id": user_id})

def create_listing_logger(listing_id: int) -> ContextLogger:
    """Create a logger with listing context."""
    logger = logging.getLogger("mandok.listing")
    return ContextLogger(logger, {"listing_id": listing_id})

class DatabaseLogger:
    """Logger for database operations."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("mandok.database")

    async def log_user_action(self, user_id: int, guild_id: int, action: str, details: dict = None):
        """Log user action to database."""
        try:
            if self.bot.db_manager:
                await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO admin_actions (admin_id, guild_id, action_type, target_id, details, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    user_id,
                    guild_id,
                    action,
                    user_id,
                    details or {},
                    datetime.now()
                )
        except Exception as e:
            self.logger.error(f"Failed to log user action: {e}")

    async def log_admin_action(self, admin_id: int, guild_id: int, action: str, target_id: int = None, details: dict = None):
        """Log admin action to database."""
        try:
            if self.bot.db_manager:
                await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO admin_actions (admin_id, guild_id, action_type, target_id, details, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    admin_id,
                    guild_id,
                    action,
                    target_id,
                    details or {},
                    datetime.now()
                )
        except Exception as e:
            self.logger.error(f"Failed to log admin action: {e}")

# Error reporting utilities
class ErrorReporter:
    """Utility for reporting errors to administrators."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("mandok.errors")

    async def report_error(self, error: Exception, context: dict = None):
        """Report error to administrators."""
        self.logger.error(f"Error reported: {error}", exc_info=True)

        # This could be extended to send notifications to admin channels
        # or integrate with error tracking services

    async def report_critical_error(self, error: Exception, context: dict = None):
        """Report critical error that needs immediate attention."""
        self.logger.critical(f"CRITICAL ERROR: {error}", exc_info=True)

        # This could send immediate notifications to administrators

    async def process_expired_events(self):
        """Process events that have reached their scheduled time"""
        try:
            current_time = datetime.now(timezone.utc)

            # Get expired events
            expired_events = await fetch_all("""
                SELECT se.*, l.user_id, l.item, l.zone, l.guild_id, l.channel_id
                FROM scheduled_events se
                JOIN listings l ON se.listing_id = l.id
                WHERE se.status = 'pending' 
                  AND se.event_time <= $1
                  AND l.active = TRUE
            """, current_time)

            for event in expired_events:
                await self._process_single_event(event)

        except Exception as e:
            logger.error(f"Error processing expire")

# Create a default logger instance for module-level imports
logger = logging.getLogger(__name__)