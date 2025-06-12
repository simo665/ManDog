import os
import logging
import discord
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Supabase configuration (if using Supabase for PostgreSQL)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Bot intents configuration
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.guild_messages = True
INTENTS.guild_reactions = True
INTENTS.members = True

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", None)

# Marketplace configuration
LISTING_EXPIRY_DAYS = int(os.getenv("LISTING_EXPIRY_DAYS", "14"))
REMINDER_HOURS_BEFORE_EXPIRY = int(os.getenv("REMINDER_HOURS_BEFORE_EXPIRY", "24"))
MAX_LISTINGS_PER_USER = int(os.getenv("MAX_LISTINGS_PER_USER", "10"))
MAX_LISTINGS_PER_ZONE = int(os.getenv("MAX_LISTINGS_PER_ZONE", "100"))

# Reputation system configuration
MIN_REPUTATION_FOR_TRADING = float(os.getenv("MIN_REPUTATION_FOR_TRADING", "0.0"))
REPUTATION_DECAY_ENABLED = os.getenv("REPUTATION_DECAY_ENABLED", "false").lower() == "true"
REPUTATION_DECAY_DAYS = int(os.getenv("REPUTATION_DECAY_DAYS", "90"))

# Role management configuration
AUTO_ROLE_MANAGEMENT = os.getenv("AUTO_ROLE_MANAGEMENT", "true").lower() == "true"
TRUSTED_TRADER_ROLE = os.getenv("TRUSTED_TRADER_ROLE", "Trusted Trader")
VERIFIED_TRADER_ROLE = os.getenv("VERIFIED_TRADER_ROLE", "Verified Trader")
RESTRICTED_TRADER_ROLE = os.getenv("RESTRICTED_TRADER_ROLE", "Restricted Trader")

# Admin configuration
ADMIN_USER_IDS = [
    int(user_id.strip()) 
    for user_id in os.getenv("ADMIN_USER_IDS", "").split(",") 
    if user_id.strip().isdigit()
]

# Bot owners configuration
BOT_OWNERS = [
    int(user_id.strip()) 
    for user_id in os.getenv("BOT_OWNERS", "").split(",") 
    if user_id.strip().isdigit()
]

ADMIN_ROLE_NAMES = [
    role.strip() 
    for role in os.getenv("ADMIN_ROLE_NAMES", "admin,administrator,mandok admin").split(",")
    if role.strip()
]

# Moderation configuration
CONTENT_FILTER_ENABLED = os.getenv("CONTENT_FILTER_ENABLED", "true").lower() == "true"
AUTO_MODERATION_ENABLED = os.getenv("AUTO_MODERATION_ENABLED", "false").lower() == "true"
SPAM_DETECTION_ENABLED = os.getenv("SPAM_DETECTION_ENABLED", "true").lower() == "true"

# Rate limiting configuration
RATE_LIMIT_LISTINGS_PER_HOUR = int(os.getenv("RATE_LIMIT_LISTINGS_PER_HOUR", "5"))
RATE_LIMIT_RATINGS_PER_DAY = int(os.getenv("RATE_LIMIT_RATINGS_PER_DAY", "10"))
RATE_LIMIT_COMMANDS_PER_MINUTE = int(os.getenv("RATE_LIMIT_COMMANDS_PER_MINUTE", "10"))

# Notification configuration
DM_NOTIFICATIONS_ENABLED = os.getenv("DM_NOTIFICATIONS_ENABLED", "true").lower() == "true"
CHANNEL_NOTIFICATIONS_ENABLED = os.getenv("CHANNEL_NOTIFICATIONS_ENABLED", "false").lower() == "true"
WEBHOOK_NOTIFICATIONS_ENABLED = os.getenv("WEBHOOK_NOTIFICATIONS_ENABLED", "false").lower() == "true"

# External service configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
ERROR_REPORTING_WEBHOOK = os.getenv("ERROR_REPORTING_WEBHOOK", "")

# Feature flags
ENABLE_QUEUE_SYSTEM = os.getenv("ENABLE_QUEUE_SYSTEM", "true").lower() == "true"
ENABLE_PARTY_FINDER = os.getenv("ENABLE_PARTY_FINDER", "false").lower() == "true"
ENABLE_ITEM_SUGGESTIONS = os.getenv("ENABLE_ITEM_SUGGESTIONS", "true").lower() == "true"
ENABLE_TRANSACTION_TRACKING = os.getenv("ENABLE_TRANSACTION_TRACKING", "true").lower() == "true"

# Timezone configuration
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "UTC")
TIMEZONE_DISPLAY_FORMAT = os.getenv("TIMEZONE_DISPLAY_FORMAT", "12h")  # 12h or 24h

# Embed configuration
EMBED_COLOR_PRIMARY = int(os.getenv("EMBED_COLOR_PRIMARY", "0x1E40AF"), 16)
EMBED_COLOR_SUCCESS = int(os.getenv("EMBED_COLOR_SUCCESS", "0x059669"), 16)
EMBED_COLOR_WARNING = int(os.getenv("EMBED_COLOR_WARNING", "0xD97706"), 16)
EMBED_COLOR_ERROR = int(os.getenv("EMBED_COLOR_ERROR", "0xDC2626"), 16)
EMBED_COLOR_WTS = int(os.getenv("EMBED_COLOR_WTS", "0xF59E0B"), 16)
EMBED_COLOR_WTB = int(os.getenv("EMBED_COLOR_WTB", "0x3B82F6"), 16)

# Performance configuration
DATABASE_POOL_MIN_SIZE = int(os.getenv("DATABASE_POOL_MIN_SIZE", "1"))
DATABASE_POOL_MAX_SIZE = int(os.getenv("DATABASE_POOL_MAX_SIZE", "10"))
DATABASE_COMMAND_TIMEOUT = int(os.getenv("DATABASE_COMMAND_TIMEOUT", "60"))

# Cache configuration
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# Backup configuration
AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "false").lower() == "true"
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))

# Development configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
DEVELOPMENT_GUILD_ID = os.getenv("DEVELOPMENT_GUILD_ID", "")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# API configuration for external services
FFXIAH_API_KEY = os.getenv("FFXIAH_API_KEY", "")
FFXIDB_API_KEY = os.getenv("FFXIDB_API_KEY", "")

# Security configuration
ENABLE_SECURITY_CHECKS = os.getenv("ENABLE_SECURITY_CHECKS", "true").lower() == "true"
MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "2000"))
ALLOWED_FILE_TYPES = [
    ext.strip() 
    for ext in os.getenv("ALLOWED_FILE_TYPES", ".png,.jpg,.jpeg,.gif").split(",")
    if ext.strip()
]

class Config:
    """Configuration class for accessing settings."""
    
    def __init__(self):
        """Initialize configuration."""
        self.validate_required_settings()
    
    def validate_required_settings(self):
        """Validate that required settings are present."""
        required_settings = [
            ("BOT_TOKEN", BOT_TOKEN),
            ("DATABASE_URL", DATABASE_URL)
        ]
        
        missing_settings = []
        for setting_name, setting_value in required_settings:
            if not setting_value:
                missing_settings.append(setting_name)
        
        if missing_settings:
            error_msg = f"Missing required environment variables: {', '.join(missing_settings)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return DEBUG_MODE or TEST_MODE
    
    @property
    def database_config(self) -> dict:
        """Get database configuration."""
        return {
            "url": DATABASE_URL,
            "min_size": DATABASE_POOL_MIN_SIZE,
            "max_size": DATABASE_POOL_MAX_SIZE,
            "command_timeout": DATABASE_COMMAND_TIMEOUT
        }
    
    @property
    def embed_colors(self) -> dict:
        """Get embed color configuration."""
        return {
            "primary": EMBED_COLOR_PRIMARY,
            "success": EMBED_COLOR_SUCCESS,
            "warning": EMBED_COLOR_WARNING,
            "error": EMBED_COLOR_ERROR,
            "wts": EMBED_COLOR_WTS,
            "wtb": EMBED_COLOR_WTB
        }
    
    @property
    def marketplace_config(self) -> dict:
        """Get marketplace configuration."""
        return {
            "listing_expiry_days": LISTING_EXPIRY_DAYS,
            "reminder_hours": REMINDER_HOURS_BEFORE_EXPIRY,
            "max_listings_per_user": MAX_LISTINGS_PER_USER,
            "max_listings_per_zone": MAX_LISTINGS_PER_ZONE,
            "min_reputation": MIN_REPUTATION_FOR_TRADING
        }
    
    @property
    def rate_limits(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "listings_per_hour": RATE_LIMIT_LISTINGS_PER_HOUR,
            "ratings_per_day": RATE_LIMIT_RATINGS_PER_DAY,
            "commands_per_minute": RATE_LIMIT_COMMANDS_PER_MINUTE
        }
    
    @property
    def feature_flags(self) -> dict:
        """Get feature flag configuration."""
        return {
            "queue_system": ENABLE_QUEUE_SYSTEM,
            "party_finder": ENABLE_PARTY_FINDER,
            "item_suggestions": ENABLE_ITEM_SUGGESTIONS,
            "transaction_tracking": ENABLE_TRANSACTION_TRACKING,
            "auto_role_management": AUTO_ROLE_MANAGEMENT,
            "content_filter": CONTENT_FILTER_ENABLED,
            "auto_moderation": AUTO_MODERATION_ENABLED,
            "spam_detection": SPAM_DETECTION_ENABLED,
            "dm_notifications": DM_NOTIFICATIONS_ENABLED,
            "caching": ENABLE_CACHING
        }
    
    def get_admin_config(self) -> dict:
        """Get admin configuration."""
        return {
            "user_ids": ADMIN_USER_IDS,
            "role_names": ADMIN_ROLE_NAMES
        }
    
    def get_role_config(self) -> dict:
        """Get role configuration."""
        return {
            "trusted_trader": TRUSTED_TRADER_ROLE,
            "verified_trader": VERIFIED_TRADER_ROLE,
            "restricted_trader": RESTRICTED_TRADER_ROLE
        }

# Create global config instance
config = Config()

def get_setting(setting_name: str, default_value: any = None) -> any:
    """Get a setting value with optional default."""
    try:
        return os.getenv(setting_name, default_value)
    except Exception as e:
        logger.error(f"Error getting setting {setting_name}: {e}")
        return default_value

def update_setting(setting_name: str, value: any) -> bool:
    """Update a setting value (for runtime configuration)."""
    try:
        os.environ[setting_name] = str(value)
        logger.info(f"Updated setting {setting_name} to {value}")
        return True
    except Exception as e:
        logger.error(f"Error updating setting {setting_name}: {e}")
        return False

def load_config_from_file(file_path: str) -> bool:
    """Load configuration from a file."""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Config file not found: {file_path}")
            return False
        
        # This could be implemented to load from JSON, YAML, etc.
        # For now, we'll just note that the functionality exists
        logger.info(f"Config file loading not implemented for {file_path}")
        return False
        
    except Exception as e:
        logger.error(f"Error loading config from file {file_path}: {e}")
        return False

def validate_configuration() -> bool:
    """Validate the current configuration."""
    try:
        # Validate required settings are present
        config.validate_required_settings()
        
        # Validate numeric settings
        numeric_settings = [
            ("LISTING_EXPIRY_DAYS", LISTING_EXPIRY_DAYS),
            ("MAX_LISTINGS_PER_USER", MAX_LISTINGS_PER_USER),
            ("DATABASE_POOL_MIN_SIZE", DATABASE_POOL_MIN_SIZE),
            ("DATABASE_POOL_MAX_SIZE", DATABASE_POOL_MAX_SIZE)
        ]
        
        for setting_name, value in numeric_settings:
            if value < 0:
                logger.error(f"Setting {setting_name} must be non-negative, got {value}")
                return False
        
        # Validate color settings
        color_settings = [
            ("EMBED_COLOR_PRIMARY", EMBED_COLOR_PRIMARY),
            ("EMBED_COLOR_SUCCESS", EMBED_COLOR_SUCCESS),
            ("EMBED_COLOR_ERROR", EMBED_COLOR_ERROR)
        ]
        
        for setting_name, value in color_settings:
            if not (0 <= value <= 0xFFFFFF):
                logger.error(f"Setting {setting_name} must be a valid hex color, got {value}")
                return False
        
        logger.info("Configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

# Print configuration status on import
def print_config_status():
    """Print current configuration status."""
    try:
        logger.info("=== Mandok Bot Configuration ===")
        logger.info(f"Debug Mode: {DEBUG_MODE}")
        logger.info(f"Test Mode: {TEST_MODE}")
        logger.info(f"Database URL: {'***CONFIGURED***' if DATABASE_URL else 'NOT SET'}")
        logger.info(f"Bot Token: {'***CONFIGURED***' if BOT_TOKEN else 'NOT SET'}")
        logger.info(f"Admin Users: {len(ADMIN_USER_IDS)} configured")
        logger.info(f"Feature Flags: {sum(config.feature_flags.values())} enabled")
        logger.info("===============================")
    except Exception as e:
        logger.error(f"Error printing config status: {e}")

if __name__ == "__main__":
    print_config_status()
    validate_configuration()
