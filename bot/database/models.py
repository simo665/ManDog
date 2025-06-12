"""
Database models and schema definitions.
"""

from typing import Dict, Any
from datetime import datetime

class DatabaseSchema:
    """Database schema definitions."""
    
    # Table creation SQL statements
    TABLES = {
        'guild_configs': """
            CREATE TABLE IF NOT EXISTS guild_configs (
                guild_id BIGINT PRIMARY KEY,
                setup_complete BOOLEAN DEFAULT FALSE,
                setup_date TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """,
        
        'marketplace_channels': """
            CREATE TABLE IF NOT EXISTS marketplace_channels (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT UNIQUE NOT NULL,
                message_id BIGINT,
                listing_type VARCHAR(10) NOT NULL CHECK (listing_type IN ('WTS', 'WTB')),
                zone VARCHAR(50) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id) ON DELETE CASCADE
            );
        """,
        
        'users': """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(100),
                reputation_avg DECIMAL(3,2) DEFAULT 0.00,
                reputation_count INTEGER DEFAULT 0,
                activity_score INTEGER DEFAULT 0,
                timezone VARCHAR(50) DEFAULT 'UTC',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """,
        
        'listings': """
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                listing_type VARCHAR(10) NOT NULL CHECK (listing_type IN ('WTS', 'WTB')),
                zone VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100) NOT NULL,
                item VARCHAR(200) NOT NULL,
                quantity INTEGER DEFAULT 1,
                notes TEXT,
                scheduled_time TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE,
                active BOOLEAN DEFAULT TRUE,
                reminded BOOLEAN DEFAULT FALSE,
                removed_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id) ON DELETE CASCADE
            );
        """,
        
        'reputation': """
            CREATE TABLE IF NOT EXISTS reputation (
                id SERIAL PRIMARY KEY,
                rater_id BIGINT NOT NULL,
                target_id BIGINT NOT NULL,
                listing_id INTEGER,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (rater_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE SET NULL,
                UNIQUE(rater_id, target_id, listing_id)
            );
        """,
        
        'ratings': """
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                rater_id BIGINT NOT NULL,
                rated_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                order_id VARCHAR(100),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                status VARCHAR(20) DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected')),
                admin_id BIGINT,
                admin_notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                reviewed_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (rater_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (rated_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE SET NULL
            );
        """,
        
        'guild_rating_configs': """
            CREATE TABLE IF NOT EXISTS guild_rating_configs (
                guild_id BIGINT PRIMARY KEY,
                admin_channel_id BIGINT,
                low_rating_threshold INTEGER DEFAULT 3,
                require_admin_approval BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id) ON DELETE CASCADE
            );
        """,
        
        'queues': """
            CREATE TABLE IF NOT EXISTS queues (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                listing_id INTEGER NOT NULL,
                queue_type VARCHAR(20) NOT NULL CHECK (queue_type IN ('buyer_queue', 'seller_queue')),
                requested_item VARCHAR(200),
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                notified BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
                UNIQUE(user_id, listing_id)
            );
        """,
        
        'transactions': """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER,
                seller_id BIGINT NOT NULL,
                buyer_id BIGINT NOT NULL,
                item VARCHAR(200) NOT NULL,
                zone VARCHAR(50) NOT NULL,
                quantity INTEGER DEFAULT 1,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')),
                seller_confirmed BOOLEAN DEFAULT FALSE,
                buyer_confirmed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE SET NULL,
                FOREIGN KEY (seller_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (buyer_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """,
        
        'admin_actions': """
            CREATE TABLE IF NOT EXISTS admin_actions (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                target_id BIGINT,
                details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id) ON DELETE CASCADE
            );
        """,
        
        'item_suggestions': """
            CREATE TABLE IF NOT EXISTS item_suggestions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                zone VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100) NOT NULL,
                item_name VARCHAR(200) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                admin_id BIGINT,
                admin_notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                reviewed_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (guild_id) REFERENCES guild_configs(guild_id) ON DELETE CASCADE,
                FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE SET NULL
            );
        """,
        
        'items': """
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                zone VARCHAR(50) NOT NULL,
                monster_name VARCHAR(100) NOT NULL,
                item_name VARCHAR(200) NOT NULL,
                added_by BIGINT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (added_by) REFERENCES users(user_id) ON DELETE SET NULL,
                UNIQUE(zone, monster_name, item_name)
            );
        """,
        
        'listing_queues': """
            CREATE TABLE IF NOT EXISTS listing_queues (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                item_name VARCHAR(200) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(listing_id, user_id, item_name)
            );
        """,
        
        'scheduled_events': """
            CREATE TABLE IF NOT EXISTS scheduled_events (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL,
                event_time TIMESTAMP WITH TIME ZONE NOT NULL,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'started', 'completed', 'cancelled')),
                seller_confirmed BOOLEAN DEFAULT FALSE,
                participants JSONB DEFAULT '[]',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
            );
        """
    }
    
    # Index creation statements for performance
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_listings_guild_zone ON listings(guild_id, zone, listing_type);",
        "CREATE INDEX IF NOT EXISTS idx_listings_user_active ON listings(user_id, active);",
        "CREATE INDEX IF NOT EXISTS idx_listings_expires ON listings(expires_at) WHERE active = TRUE;",
        "CREATE INDEX IF NOT EXISTS idx_reputation_target ON reputation(target_id);",
        "CREATE INDEX IF NOT EXISTS idx_queues_listing ON queues(listing_id);",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_channels_guild ON marketplace_channels(guild_id);",
        "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);",
    ]
    
    @classmethod
    def get_create_statements(cls) -> Dict[str, str]:
        """Get all table creation statements."""
        return cls.TABLES
    
    @classmethod
    def get_index_statements(cls) -> list:
        """Get all index creation statements."""
        return cls.INDEXES

class ListingModel:
    """Model for marketplace listings."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.guild_id = data.get('guild_id')
        self.listing_type = data.get('listing_type')
        self.zone = data.get('zone')
        self.subcategory = data.get('subcategory')
        self.item = data.get('item')
        self.quantity = data.get('quantity', 1)
        self.notes = data.get('notes', '')
        self.scheduled_time = data.get('scheduled_time')
        self.created_at = data.get('created_at')
        self.expires_at = data.get('expires_at')
        self.active = data.get('active', True)
        self.reminded = data.get('reminded', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'guild_id': self.guild_id,
            'listing_type': self.listing_type,
            'zone': self.zone,
            'subcategory': self.subcategory,
            'item': self.item,
            'quantity': self.quantity,
            'notes': self.notes,
            'scheduled_time': self.scheduled_time,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'active': self.active,
            'reminded': self.reminded
        }
    
    def is_expired(self) -> bool:
        """Check if listing is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

class UserModel:
    """Model for user data."""
    
    def __init__(self, data: Dict[str, Any]):
        self.user_id = data.get('user_id')
        self.username = data.get('username')
        self.reputation_avg = float(data.get('reputation_avg', 0.0))
        self.reputation_count = data.get('reputation_count', 0)
        self.activity_score = data.get('activity_score', 0)
        self.timezone = data.get('timezone', 'UTC')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'reputation_avg': self.reputation_avg,
            'reputation_count': self.reputation_count,
            'activity_score': self.activity_score,
            'timezone': self.timezone,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def get_reputation_stars(self) -> str:
        """Get star representation of reputation."""
        full_stars = int(self.reputation_avg)
        empty_stars = 5 - full_stars
        return "⭐" * full_stars + "☆" * empty_stars

class ReputationModel:
    """Model for reputation ratings."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.rater_id = data.get('rater_id')
        self.target_id = data.get('target_id')
        self.listing_id = data.get('listing_id')
        self.rating = data.get('rating')
        self.comment = data.get('comment', '')
        self.created_at = data.get('created_at')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'rater_id': self.rater_id,
            'target_id': self.target_id,
            'listing_id': self.listing_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at
        }
