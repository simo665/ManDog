
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from bot.utils.permissions import is_admin

logger = logging.getLogger(__name__)

class RatingCommands(commands.Cog):
    """Commands for managing ratings and reputation."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="logsrates", description="Set the channel for rating logs and summaries")
    async def set_logs_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for rating logs and summaries."""
        try:
            if not is_admin(interaction.user, interaction.guild):
                await interaction.response.send_message(
                    "❌ You need admin permissions to use this command.", ephemeral=True
                )
                return

            # Update or create guild rating config
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO guild_rating_configs (guild_id, admin_channel_id, created_at, updated_at)
                VALUES ($1, $2, NOW(), NOW())
                ON CONFLICT (guild_id)
                DO UPDATE SET 
                    admin_channel_id = $2,
                    updated_at = NOW()
                """,
                interaction.guild.id, channel.id
            )

            await interaction.response.send_message(
                f"✅ Rating logs channel set to {channel.mention}\n"
                f"Rating summaries will be posted here after trades are completed.",
                ephemeral=True
            )

            logger.info(f"Set rating logs channel to {channel.id} for guild {interaction.guild.id}")

        except Exception as e:
            logger.error(f"Error setting logs channel: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while setting the logs channel.", ephemeral=True
            )

    @app_commands.command(name="userrating", description="View a user's rating and reputation")
    async def view_user_rating(self, interaction: discord.Interaction, user: discord.Member):
        """View a user's rating and reputation."""
        try:
            # Get user's rating data
            user_data = await self.bot.db_manager.execute_query(
                """
                SELECT 
                    reputation_avg,
                    reputation_count,
                    activity_score,
                    created_at
                FROM users 
                WHERE user_id = $1
                """,
                user.id
            )

            if not user_data or user_data[0]['reputation_count'] == 0:
                embed = discord.Embed(
                    title="📊 User Rating",
                    description=f"{user.mention} has not received any ratings yet.",
                    color=0x6B7280
                )
                await interaction.response.send_message(embed=embed)
                return

            data = user_data[0]
            avg_rating = float(data['reputation_avg'])
            rating_count = data['reputation_count']
            activity_score = data['activity_score']

            # Get recent ratings
            recent_ratings = await self.bot.db_manager.execute_query(
                """
                SELECT rating, comment, created_at
                FROM event_ratings
                WHERE seller_id = $1
                ORDER BY created_at DESC
                LIMIT 5
                """,
                user.id
            )

            # Create embed
            embed = discord.Embed(
                title="📊 User Rating",
                description=f"Rating information for {user.mention}",
                color=0x3B82F6
            )

            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)

            # Rating summary
            stars = "⭐" * int(avg_rating) + "☆" * (5 - int(avg_rating))
            embed.add_field(
                name="⭐ Average Rating",
                value=f"{avg_rating:.1f}/5 {stars}",
                inline=True
            )

            embed.add_field(
                name="📊 Total Ratings",
                value=str(rating_count),
                inline=True
            )

            embed.add_field(
                name="🏃 Activity Score",
                value=str(activity_score),
                inline=True
            )

            # Recent ratings
            if recent_ratings:
                recent_text = ""
                for rating in recent_ratings:
                    rating_stars = "⭐" * rating['rating']
                    recent_text += f"{rating_stars} ({rating['rating']}/5)\n"
                    if rating['comment']:
                        recent_text += f"💬 *{rating['comment'][:50]}{'...' if len(rating['comment']) > 50 else ''}*\n"
                    recent_text += "\n"

                if recent_text:
                    embed.add_field(
                        name="🕒 Recent Ratings",
                        value=recent_text[:1024],
                        inline=False
                    )

            embed.set_footer(text=f"Member since {data['created_at'].strftime('%B %Y') if data['created_at'] else 'Unknown'}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error viewing user rating: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while retrieving user rating.", ephemeral=True
            )

    @app_commands.command(name="topraters", description="View the leaderboard of top-rated sellers")
    async def top_rated_sellers(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """View the leaderboard of top-rated sellers."""
        try:
            if limit > 20:
                limit = 20

            # Get top rated users
            top_users = await self.bot.db_manager.execute_query(
                """
                SELECT 
                    user_id,
                    reputation_avg,
                    reputation_count,
                    activity_score
                FROM users 
                WHERE reputation_count >= 3
                ORDER BY reputation_avg DESC, reputation_count DESC
                LIMIT $1
                """,
                limit
            )

            if not top_users:
                embed = discord.Embed(
                    title="🏆 Top Rated Sellers",
                    description="No users with sufficient ratings found.",
                    color=0x6B7280
                )
                await interaction.response.send_message(embed=embed)
                return

            embed = discord.Embed(
                title="🏆 Top Rated Sellers",
                description=f"Top {len(top_users)} highest rated sellers in this server",
                color=0xFFD700
            )

            leaderboard_text = ""
            for i, user_data in enumerate(top_users, 1):
                user_id = user_data['user_id']
                avg_rating = float(user_data['reputation_avg'])
                rating_count = user_data['reputation_count']
                
                # Get medal emoji
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                stars = "⭐" * int(avg_rating)
                leaderboard_text += f"{medal} <@{user_id}> - {avg_rating:.1f}/5 {stars} ({rating_count} ratings)\n"

            embed.add_field(
                name="Rankings",
                value=leaderboard_text,
                inline=False
            )

            embed.set_footer(text="Minimum 3 ratings required • Based on average rating")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while retrieving the leaderboard.", ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RatingCommands(bot))
