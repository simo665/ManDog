"""
Reputation and rating system services.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ReputationService:
    """Service for managing user reputation and ratings."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def add_rating(self, rater_id: int, target_id: int, listing_id: int, rating: int, comment: str = "") -> bool:
        """Add a rating for a user."""
        try:
            # Validate rating
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
            
            # Check if users are the same
            if rater_id == target_id:
                raise ValueError("Cannot rate yourself")
            
            # Add rating
            success = await self.bot.db_manager.add_reputation(
                rater_id, target_id, listing_id, rating, comment
            )
            
            if success:
                # Update activity scores
                await self.update_activity_scores(rater_id, target_id)
                
                # Check for role updates
                await self.check_reputation_roles(target_id)
                
                logger.info(f"Added rating {rating} from {rater_id} to {target_id}")
                return True
            
        except Exception as e:
            logger.error(f"Error adding rating: {e}")
            raise
        
        return False
    
    async def update_activity_scores(self, rater_id: int, target_id: int):
        """Update activity scores for rating participants."""
        try:
            # Update rater activity (for giving rating)
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO users (user_id, activity_score, updated_at)
                VALUES ($1, 2, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    activity_score = users.activity_score + 2,
                    updated_at = $2
                """,
                rater_id, datetime.now(timezone.utc)
            )
            
            # Update target activity (for receiving rating)
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO users (user_id, activity_score, updated_at)
                VALUES ($1, 3, $2)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    activity_score = users.activity_score + 3,
                    updated_at = $2
                """,
                target_id, datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error updating activity scores: {e}")
    
    async def check_reputation_roles(self, user_id: int):
        """Check and update reputation-based roles."""
        try:
            # Get user reputation
            user_data = await self.bot.db_manager.get_user_reputation(user_id)
            
            if not user_data:
                return
            
            avg_rating = user_data['reputation_avg']
            rating_count = user_data['reputation_count']
            
            # Define role thresholds
            role_rules = [
                {'min_rating': 4.5, 'min_count': 10, 'role': 'trusted_trader'},
                {'min_rating': 4.0, 'min_count': 5, 'role': 'verified_trader'},
                {'min_rating': 0.0, 'max_rating': 2.5, 'min_count': 3, 'role': 'restricted_trader'}
            ]
            
            # Check which roles apply
            applicable_roles = []
            for rule in role_rules:
                if rating_count >= rule['min_count']:
                    if 'max_rating' in rule:
                        if rule['min_rating'] <= avg_rating <= rule['max_rating']:
                            applicable_roles.append(rule['role'])
                    else:
                        if avg_rating >= rule['min_rating']:
                            applicable_roles.append(rule['role'])
            
            # Store role updates (this would be processed by a role management system)
            if applicable_roles:
                await self.store_role_updates(user_id, applicable_roles)
            
        except Exception as e:
            logger.error(f"Error checking reputation roles: {e}")
    
    async def store_role_updates(self, user_id: int, roles: List[str]):
        """Store role updates for processing."""
        try:
            for role in roles:
                await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO admin_actions (admin_id, action_type, target_id, details, created_at)
                    VALUES ($1, 'role_update', $2, $3, $4)
                    """,
                    self.bot.user.id,  # Bot as admin
                    user_id,
                    {'role': role, 'action': 'assign'},
                    datetime.now(timezone.utc)
                )
            
        except Exception as e:
            logger.error(f"Error storing role updates: {e}")
    
    async def get_user_reputation_details(self, user_id: int) -> Dict[str, Any]:
        """Get detailed reputation information for a user."""
        try:
            # Get basic reputation data
            user_data = await self.bot.db_manager.get_user_reputation(user_id)
            
            # Get recent ratings
            recent_ratings = await self.bot.db_manager.execute_query(
                """
                SELECT r.rating, r.comment, r.created_at, u.username as rater_name
                FROM reputation r
                LEFT JOIN users u ON r.rater_id = u.user_id
                WHERE r.target_id = $1
                ORDER BY r.created_at DESC
                LIMIT 10
                """,
                user_id
            )
            
            # Get rating distribution
            rating_distribution = await self.bot.db_manager.execute_query(
                """
                SELECT rating, COUNT(*) as count
                FROM reputation
                WHERE target_id = $1
                GROUP BY rating
                ORDER BY rating DESC
                """,
                user_id
            )
            
            # Calculate additional metrics
            total_ratings = user_data['reputation_count']
            if total_ratings > 0:
                recent_trend = await self.calculate_recent_trend(user_id)
            else:
                recent_trend = 0.0
            
            return {
                **user_data,
                'recent_ratings': recent_ratings,
                'rating_distribution': rating_distribution,
                'recent_trend': recent_trend,
                'reliability_score': self.calculate_reliability_score(user_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting reputation details: {e}")
            return {}
    
    async def calculate_recent_trend(self, user_id: int) -> float:
        """Calculate recent rating trend for a user."""
        try:
            # Get ratings from last 30 days vs previous 30 days
            recent_ratings = await self.bot.db_manager.execute_query(
                """
                SELECT AVG(rating) as avg_rating
                FROM reputation
                WHERE target_id = $1 
                  AND created_at > NOW() - INTERVAL '30 days'
                """,
                user_id
            )
            
            previous_ratings = await self.bot.db_manager.execute_query(
                """
                SELECT AVG(rating) as avg_rating
                FROM reputation
                WHERE target_id = $1 
                  AND created_at BETWEEN NOW() - INTERVAL '60 days' AND NOW() - INTERVAL '30 days'
                """,
                user_id
            )
            
            recent_avg = recent_ratings[0]['avg_rating'] if recent_ratings and recent_ratings[0]['avg_rating'] else 0.0
            previous_avg = previous_ratings[0]['avg_rating'] if previous_ratings and previous_ratings[0]['avg_rating'] else 0.0
            
            if previous_avg > 0:
                return round(recent_avg - previous_avg, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating recent trend: {e}")
            return 0.0
    
    def calculate_reliability_score(self, user_data: Dict[str, Any]) -> float:
        """Calculate a reliability score based on reputation and activity."""
        try:
            avg_rating = user_data['reputation_avg']
            rating_count = user_data['reputation_count']
            activity_score = user_data['activity_score']
            
            # Base score from average rating (0-100)
            base_score = (avg_rating / 5.0) * 100
            
            # Confidence modifier based on number of ratings
            confidence = min(rating_count / 10.0, 1.0)  # Full confidence at 10+ ratings
            
            # Activity modifier (bonus for active users)
            activity_modifier = min(activity_score / 100.0, 0.2)  # Max 20% bonus
            
            # Calculate final score
            reliability_score = base_score * confidence + (base_score * activity_modifier)
            
            return round(min(reliability_score, 100.0), 1)
            
        except Exception as e:
            logger.error(f"Error calculating reliability score: {e}")
            return 0.0
    
    async def get_reputation_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get reputation leaderboard for a guild."""
        try:
            leaderboard = await self.bot.db_manager.execute_query(
                """
                SELECT 
                    u.user_id,
                    u.username,
                    u.reputation_avg,
                    u.reputation_count,
                    u.activity_score,
                    COUNT(l.id) as total_listings
                FROM users u
                LEFT JOIN listings l ON u.user_id = l.user_id AND l.guild_id = $1
                WHERE u.reputation_count > 0
                GROUP BY u.user_id, u.username, u.reputation_avg, u.reputation_count, u.activity_score
                ORDER BY u.reputation_avg DESC, u.reputation_count DESC
                LIMIT $2
                """,
                guild_id, limit
            )
            
            # Add reliability scores
            for entry in leaderboard:
                entry['reliability_score'] = self.calculate_reliability_score(entry)
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting reputation leaderboard: {e}")
            return []
    
    async def moderate_reputation(self, moderator_id: int, target_id: int, action: str, reason: str) -> bool:
        """Moderate user reputation (admin action)."""
        try:
            actions = {
                'reset': self.reset_user_reputation,
                'adjust': self.adjust_user_reputation,
                'flag': self.flag_user_reputation
            }
            
            if action not in actions:
                raise ValueError(f"Invalid moderation action: {action}")
            
            # Log admin action
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO admin_actions (admin_id, action_type, target_id, details, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                moderator_id,
                f"reputation_{action}",
                target_id,
                {'reason': reason},
                datetime.now(timezone.utc)
            )
            
            # Perform the action
            return await actions[action](target_id, reason)
            
        except Exception as e:
            logger.error(f"Error moderating reputation: {e}")
            return False
    
    async def reset_user_reputation(self, user_id: int, reason: str) -> bool:
        """Reset a user's reputation (admin action)."""
        try:
            # Archive current reputation
            await self.bot.db_manager.execute_command(
                """
                UPDATE reputation 
                SET comment = CONCAT(comment, ' [ARCHIVED: ', $2, ']')
                WHERE target_id = $1
                """,
                user_id, reason
            )
            
            # Reset user stats
            await self.bot.db_manager.execute_command(
                """
                UPDATE users 
                SET reputation_avg = 0.0, reputation_count = 0
                WHERE user_id = $1
                """,
                user_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting reputation: {e}")
            return False
    
    async def adjust_user_reputation(self, user_id: int, reason: str) -> bool:
        """Adjust user reputation (placeholder for future implementation)."""
        # This would implement reputation adjustments
        return True
    
    async def flag_user_reputation(self, user_id: int, reason: str) -> bool:
        """Flag user reputation for review."""
        # This would implement reputation flagging
        return True
