"""
Permission checking utilities for the marketplace bot.
"""

import logging
import discord
from typing import Union, List

logger = logging.getLogger(__name__)

def is_admin(user: Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
    """Check if user has admin permissions."""
    try:
        if not isinstance(user, discord.Member):
            # If user is not a Member, get the member from guild
            member = guild.get_member(user.id)
            if not member:
                return False
            user = member
        
        # Check if user has administrator permission
        if user.guild_permissions.administrator:
            return True
        
        # Check if user is the guild owner
        if user.id == guild.owner_id:
            return True
        
        # Check for specific admin roles (customizable)
        admin_role_names = ['admin', 'administrator', 'mandok admin', 'marketplace admin']
        for role in user.roles:
            if role.name.lower() in admin_role_names:
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking admin permissions for user {user.id}: {e}")
        return False

def is_moderator(user: Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
    """Check if user has moderator permissions."""
    try:
        if not isinstance(user, discord.Member):
            member = guild.get_member(user.id)
            if not member:
                return False
            user = member
        
        # Admin users are also moderators
        if is_admin(user, guild):
            return True
        
        # Check for moderator permissions
        if user.guild_permissions.manage_messages or user.guild_permissions.manage_roles:
            return True
        
        # Check for specific moderator roles
        mod_role_names = ['mod', 'moderator', 'mandok mod', 'marketplace mod']
        for role in user.roles:
            if role.name.lower() in mod_role_names:
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking moderator permissions for user {user.id}: {e}")
        return False

def can_manage_listings(user: Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
    """Check if user can manage marketplace listings."""
    try:
        # Admins and moderators can manage listings
        return is_moderator(user, guild)
        
    except Exception as e:
        logger.error(f"Error checking listing management permissions for user {user.id}: {e}")
        return False

def can_use_marketplace(user: Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
    """Check if user can use the marketplace."""
    try:
        if not isinstance(user, discord.Member):
            member = guild.get_member(user.id)
            if not member:
                return False
            user = member
        
        # Check if user is not timed out/muted
        if user.timed_out_until:
            return False
        
        # Check for restricted trader role (low reputation)
        restricted_roles = ['restricted trader', 'marketplace restricted', 'low reputation']
        for role in user.roles:
            if role.name.lower() in restricted_roles:
                return False
        
        # Check basic permissions
        marketplace_permissions = [
            discord.Permissions.send_messages,
            discord.Permissions.use_application_commands,
            discord.Permissions.read_message_history
        ]
        
        # Get permissions for marketplace channels (this would need channel context)
        # For now, check general guild permissions
        if not user.guild_permissions.send_messages:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking marketplace permissions for user {user.id}: {e}")
        return False

def can_rate_users(user: Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
    """Check if user can rate other users."""
    try:
        if not isinstance(user, discord.Member):
            member = guild.get_member(user.id)
            if not member:
                return False
            user = member
        
        # Must be able to use marketplace
        if not can_use_marketplace(user, guild):
            return False
        
        # Check if user has been in guild long enough (prevent abuse)
        if user.joined_at:
            from datetime import datetime, timezone, timedelta
            min_membership_time = datetime.now(timezone.utc) - timedelta(days=7)
            if user.joined_at > min_membership_time:
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking rating permissions for user {user.id}: {e}")
        return False

def has_role(user: Union[discord.User, discord.Member], role_names: List[str], guild: discord.Guild) -> bool:
    """Check if user has any of the specified roles."""
    try:
        if not isinstance(user, discord.Member):
            member = guild.get_member(user.id)
            if not member:
                return False
            user = member
        
        user_role_names = [role.name.lower() for role in user.roles]
        role_names_lower = [name.lower() for name in role_names]
        
        return any(role_name in user_role_names for role_name in role_names_lower)
        
    except Exception as e:
        logger.error(f"Error checking roles for user {user.id}: {e}")
        return False

def get_user_permission_level(user: Union[discord.User, discord.Member], guild: discord.Guild) -> str:
    """Get user's permission level as a string."""
    try:
        if is_admin(user, guild):
            return "admin"
        elif is_moderator(user, guild):
            return "moderator"
        elif can_use_marketplace(user, guild):
            return "user"
        else:
            return "restricted"
            
    except Exception as e:
        logger.error(f"Error getting permission level for user {user.id}: {e}")
        return "restricted"

def check_channel_permissions(user: Union[discord.User, discord.Member], channel: discord.TextChannel, 
                            required_permissions: List[str]) -> bool:
    """Check if user has required permissions in a specific channel."""
    try:
        if not isinstance(user, discord.Member):
            member = channel.guild.get_member(user.id)
            if not member:
                return False
            user = member
        
        user_permissions = channel.permissions_for(user)
        
        permission_mapping = {
            'read_messages': user_permissions.read_messages,
            'send_messages': user_permissions.send_messages,
            'embed_links': user_permissions.embed_links,
            'attach_files': user_permissions.attach_files,
            'read_message_history': user_permissions.read_message_history,
            'use_application_commands': user_permissions.use_application_commands,
            'add_reactions': user_permissions.add_reactions,
            'manage_messages': user_permissions.manage_messages,
            'manage_channels': user_permissions.manage_channels,
            'administrator': user_permissions.administrator
        }
        
        return all(permission_mapping.get(perm, False) for perm in required_permissions)
        
    except Exception as e:
        logger.error(f"Error checking channel permissions for user {user.id}: {e}")
        return False

class PermissionDecorator:
    """Decorator class for permission checking."""
    
    @staticmethod
    def require_admin(func):
        """Decorator to require admin permissions."""
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not is_admin(interaction.user, interaction.guild):
                await interaction.response.send_message(
                    "❌ You must be an administrator to use this command.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    
    @staticmethod
    def require_moderator(func):
        """Decorator to require moderator permissions."""
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not is_moderator(interaction.user, interaction.guild):
                await interaction.response.send_message(
                    "❌ You must be a moderator to use this command.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    
    @staticmethod
    def require_marketplace_access(func):
        """Decorator to require marketplace access."""
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not can_use_marketplace(interaction.user, interaction.guild):
                await interaction.response.send_message(
                    "❌ You don't have permission to use the marketplace.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper

# Permission level constants
class PermissionLevel:
    """Permission level constants."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    RESTRICTED = "restricted"

# Role name constants for consistency
class RoleNames:
    """Standard role names used by the bot."""
    ADMIN_ROLES = ['admin', 'administrator', 'mandok admin', 'marketplace admin']
    MODERATOR_ROLES = ['mod', 'moderator', 'mandok mod', 'marketplace mod']
    TRUSTED_TRADER = 'trusted trader'
    VERIFIED_TRADER = 'verified trader'
    RESTRICTED_TRADER = 'restricted trader'
    BLACKLISTED = 'blacklisted'

def get_reputation_role(reputation_avg: float, reputation_count: int) -> str:
    """Get the appropriate reputation role based on user stats."""
    try:
        if reputation_count >= 10 and reputation_avg >= 4.5:
            return RoleNames.TRUSTED_TRADER
        elif reputation_count >= 5 and reputation_avg >= 4.0:
            return RoleNames.VERIFIED_TRADER
        elif reputation_count >= 3 and reputation_avg <= 2.5:
            return RoleNames.RESTRICTED_TRADER
        else:
            return None  # No special role
            
    except Exception as e:
        logger.error(f"Error determining reputation role: {e}")
        return None

async def update_user_roles(bot, user_id: int, guild_id: int):
    """Update user roles based on their reputation."""
    try:
        guild = bot.get_guild(guild_id)
        if not guild:
            return
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        # Get user reputation
        user_data = await bot.db_manager.get_user_reputation(user_id)
        
        # Determine appropriate role
        target_role_name = get_reputation_role(
            user_data.get('reputation_avg', 0.0),
            user_data.get('reputation_count', 0)
        )
        
        # Get all reputation roles
        all_rep_roles = [
            RoleNames.TRUSTED_TRADER,
            RoleNames.VERIFIED_TRADER,
            RoleNames.RESTRICTED_TRADER
        ]
        
        # Remove existing reputation roles
        roles_to_remove = []
        for role in member.roles:
            if role.name.lower() in [r.lower() for r in all_rep_roles]:
                roles_to_remove.append(role)
        
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Reputation role update")
        
        # Add new role if applicable
        if target_role_name:
            target_role = discord.utils.get(guild.roles, name=target_role_name)
            if not target_role:
                # Create the role if it doesn't exist
                target_role = await guild.create_role(
                    name=target_role_name,
                    reason="Marketplace reputation role"
                )
            
            await member.add_roles(target_role, reason="Reputation role assignment")
            logger.info(f"Updated reputation role for user {user_id} to {target_role_name}")
        
    except Exception as e:
        logger.error(f"Error updating user roles for {user_id}: {e}")
