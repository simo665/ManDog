"""
Database models and schema definitions.
"""

from typing import Dict, Any
from datetime import datetime, timezone

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
        """,

        'event_confirmations': """
            CREATE TABLE IF NOT EXISTS event_confirmations (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                role VARCHAR(10) NOT NULL CHECK (role IN ('seller', 'buyer')),
                confirmed BOOLEAN NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (event_id) REFERENCES scheduled_events(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(event_id, user_id)
            );
        """,

        'event_ratings': """
            CREATE TABLE IF NOT EXISTS event_ratings (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                rater_id BIGINT NOT NULL,
                seller_id BIGINT NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (event_id) REFERENCES scheduled_events(id) ON DELETE CASCADE,
                FOREIGN KEY (rater_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (seller_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(event_id, rater_id)
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

class ScheduledEventQueries:
    """Scheduled event queries."""

    def __init__(self, db):
        """Initialize with database connection."""
        self.db = db

    async def create_event(self, listing_id, event_time):
        """Create a scheduled event."""
        return await self.db.execute(
            """
            INSERT INTO scheduled_events (listing_id, event_time)
            VALUES ($1, $2)
            """,
            listing_id,
            event_time
        )

    async def get_event(self, event_id):
        """Get a scheduled event by ID."""
        return await self.db.fetch_one(
            """
            SELECT * FROM scheduled_events WHERE id = $1
            """,
            event_id
        )

    async def get_events_by_listing(self, listing_id):
        """Get scheduled events for a listing."""
        return await self.db.fetch_all(
            """
            SELECT * FROM scheduled_events WHERE listing_id = $1
            """,
            listing_id
        )

    async def update_event_status(self, event_id, status):
        """Update the status of a scheduled event."""
        return await self.db.execute(
            """
            UPDATE scheduled_events SET status = $2 WHERE id = $1
            """,
            event_id,
            status
        )

    async def confirm_seller(self, event_id):
        """Confirm seller for a scheduled event."""
        return await self.db.execute(
            """
            UPDATE scheduled_events SET seller_confirmed = TRUE WHERE id = $1
            """,
            event_id
        )

    async def add_participant(self, event_id, user_id):
        """Add a participant to a scheduled event."""
        return await self.db.execute(
            """
            UPDATE scheduled_events
            SET participants = participants || $2::jsonb
            WHERE id = $1
            """,
            event_id,
            f'[{user_id}]'
        )

    async def remove_participant(self, event_id, user_id):
        """Remove a participant from a scheduled event."""
        return await self.db.execute(
            """
            UPDATE scheduled_events
            SET participants = participants - $2
            WHERE id = $1
            """,
            event_id,
            user_id
        )

    async def get_participants(self, event_id):
        """Get participants of a scheduled event."""
        event = await self.get_event(event_id)
        if event:
            return event['participants']
        return []

    async def check_confirmation(self, event_id, user_id, role):
        """Check if a user has confirmed participation."""
        result = await self.db.fetch_one(
            """
            SELECT confirmed FROM event_confirmations
            WHERE event_id = $1 AND user_id = $2 AND role = $3
            """,
            event_id,
            user_id,
            role
        )
        return result['confirmed'] if result else False

    async def add_confirmation(self, event_id, user_id, role, confirmed):
        """Add a confirmation record."""
        await self.db.execute(
            """
            INSERT INTO event_confirmations (event_id, user_id, role, confirmed)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (event_id, user_id) DO UPDATE SET confirmed = $4
            """,
            event_id,
            user_id,
            role,
            confirmed
        )

    async def get_pending_events(self):
        """Get events that are ready to trigger."""
        return await self.db.execute_query(
            """
            SELECT se.*, l.user_id, l.item, l.zone, l.guild_id
            FROM scheduled_events se
            JOIN listings l ON se.listing_id = l.id
            WHERE se.status = 'pending' 
              AND se.event_time <= $1
              AND l.active = TRUE
            """,
            datetime.now(timezone.utc)
        )

    async def get_pending_events_for_notification(self, notification_time):
        """Get events that should send 30-minute notification."""
        return await self.db.execute_query(
            """
            SELECT se.*, l.user_id, l.item, l.zone, l.guild_id
            FROM scheduled_events se
            JOIN listings l ON se.listing_id = l.id
            WHERE se.status = 'pending' 
              AND se.event_time <= $1
              AND se.event_time > $2
              AND l.active = TRUE
            """,
            notification_time,
            datetime.now(timezone.utc)
        )