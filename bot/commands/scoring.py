
"""
Commands for viewing user scores and statistics.
"""

import discord
from discord.ext import commands
import logging
from typing import Dict, Any

from bot.ui.embeds import MarketplaceEmbeds
from bot.services.reputation import ReputationService
from bot.services.marketplace import MarketplaceService
from bot.services.ordering import OrderingService

logger = logging.getLogger(__name__)

class ScoringCommands(commands.Cog):
    """Commands for scoring and statistics."""
    
    def __init__(self, bot):
        self.bot = bot
        self.embeds = MarketplaceEmbeds()
        self.reputation_service = ReputationService(bot)
        self.marketplace_service = MarketplaceService(bot)
        self.ordering_service = OrderingService(bot)
    
    @discord.app_commands.command(name="profile", description="View your trading profile and scores")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        """View trading profile and comprehensive scores."""
        try:
            # Use command user if no user specified
            target_user = user or interaction.user
            
            # Get user statistics
            user_stats = await self.marketplace_service.get_user_statistics(
                target_user.id, interaction.guild.id
            )
            
            # Get transaction statistics
            transaction_stats = {
                'total_transactions': user_stats.get('total_transactions', 0),
                'completed_transactions': user_stats.get('completed_transactions', 0)
            }
            
            # Calculate comprehensive trader score
            trader_scores = self.reputation_service.calculate_trader_score(user_stats, transaction_stats)
            
            # Get recent order history
            order_history = await self.ordering_service.get_user_order_history(
                target_user.id, interaction.guild.id, 5
            )
            
            # Create profile embed
            embed = await self.create_profile_embed(target_user, user_stats, trader_scores, order_history)
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
            
        except Exception as e:
            logger.error(f"Error showing profile: {e}")
            await interaction.response.send_message(
                "An error occurred while loading the profile.", ephemeral=True
            )
    
    async def create_profile_embed(self, user: discord.Member, user_stats: Dict[str, Any], 
                                 trader_scores: Dict[str, Any], order_history: list):
        """Create comprehensive profile embed."""
        embed = discord.Embed(
            title=f"📊 Trading Profile - {user.display_name}",
            color=self.embeds.COLORS['primary'],
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Overall trader score with tier
        overall_score = trader_scores['overall_score']
        trader_tier = trader_scores['trader_tier']
        experience_level = trader_scores['experience_level']
        
        # Score color based on performance
        if overall_score >= 80:
            score_emoji = "🟢"
        elif overall_score >= 60:
            score_emoji = "🟡"
        else:
            score_emoji = "🔴"
        
        embed.add_field(
            name="🏆 Overall Trader Score",
            value=f"{score_emoji} **{overall_score}/100**\n**{trader_tier}** • {experience_level}",
            inline=True
        )
        
        # Reputation breakdown
        rep_avg = user_stats.get('reputation_avg', 0.0)
        rep_count = user_stats.get('reputation_count', 0)
        stars = "⭐" * int(rep_avg) + "☆" * (5 - int(rep_avg))
        
        embed.add_field(
            name="⭐ Reputation",
            value=f"{stars}\n{rep_avg:.1f}/5.0 ({rep_count} ratings)",
            inline=True
        )
        
        # Activity score
        activity_score = user_stats.get('activity_score', 0)
        embed.add_field(
            name="🎯 Activity Score",
            value=f"**{activity_score}** points\n{trader_scores['activity_score']:.1f}/100",
            inline=True
        )
        
        # Detailed score breakdown
        embed.add_field(
            name="📈 Score Breakdown",
            value=(
                f"**Reputation:** {trader_scores['reputation_score']:.1f}/100\n"
                f"**Transactions:** {trader_scores['transaction_score']:.1f}/100\n"
                f"**Activity:** {trader_scores['activity_score']:.1f}/100\n"
                f"**Consistency:** {trader_scores['consistency_score']:.1f}/100"
            ),
            inline=True
        )
        
        # Trading statistics
        total_listings = user_stats.get('total_listings', 0)
        active_listings = user_stats.get('active_listings', 0)
        wts_count = user_stats.get('wts_count', 0)
        wtb_count = user_stats.get('wtb_count', 0)
        total_transactions = user_stats.get('total_transactions', 0)
        completed_transactions = user_stats.get('completed_transactions', 0)
        
        completion_rate = (completed_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        embed.add_field(
            name="📊 Trading Statistics",
            value=(
                f"**Total Listings:** {total_listings}\n"
                f"**Active Listings:** {active_listings}\n"
                f"**WTS/WTB:** {wts_count}/{wtb_count}\n"
                f"**Completion Rate:** {completion_rate:.1f}%"
            ),
            inline=True
        )
        
        # Recent transaction history
        if order_history:
            history_text = ""
            for order in order_history[:3]:  # Show last 3 orders
                status_emoji = {
                    'completed': '✅',
                    'confirmed': '🤝',
                    'pending': '⏳',
                    'cancelled': '❌'
                }.get(order['status'], '❓')
                
                history_text += f"{status_emoji} {order['item']} • <t:{int(order['created_at'].timestamp())}:R>\n"
            
            embed.add_field(
                name="📋 Recent Orders",
                value=history_text or "No recent orders",
                inline=False
            )
        
        # Add user join date
        embed.set_footer(text=f"Trader since {user_stats.get('created_at', discord.utils.utcnow()).strftime('%B %Y')}")
        
        return embed
    
    @discord.app_commands.command(name="leaderboard", description="View the trading leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show trading leaderboard."""
        try:
            # Get reputation leaderboard
            leaderboard = await self.reputation_service.get_reputation_leaderboard(
                interaction.guild.id, 10
            )
            
            embed = discord.Embed(
                title="🏆 Trading Leaderboard",
                description="Top traders by reputation and activity",
                color=self.embeds.COLORS['primary'],
                timestamp=discord.utils.utcnow()
            )
            
            if not leaderboard:
                embed.add_field(
                    name="No Data",
                    value="No traders have been rated yet.",
                    inline=False
                )
            else:
                leaderboard_text = ""
                for i, entry in enumerate(leaderboard, 1):
                    # Get user
                    user = self.bot.get_user(entry['user_id'])
                    username = user.display_name if user else entry['username'] or f"User {entry['user_id']}"
                    
                    # Medal emojis for top 3
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                    
                    stars = "⭐" * int(entry['reputation_avg'])
                    reliability = entry.get('reliability_score', 0)
                    
                    leaderboard_text += (
                        f"{medal} **{username}**\n"
                        f"    {stars} {entry['reputation_avg']:.1f}/5 • "
                        f"⚡{reliability:.0f} • {entry['reputation_count']} ratings\n\n"
                    )
                
                embed.add_field(
                    name="🌟 Top Traders",
                    value=leaderboard_text,
                    inline=False
                )
            
            embed.set_footer(text="Rankings based on reputation average and rating count")
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
            
        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}")
            await interaction.response.send_message(
                "An error occurred while loading the leaderboard.", ephemeral=True
            )
    
    @discord.app_commands.command(name="orders", description="View your order history")
    async def orders(self, interaction: discord.Interaction):
        """View order history."""
        try:
            # Get user's order history
            orders = await self.ordering_service.get_user_order_history(
                interaction.user.id, interaction.guild.id, 15
            )
            
            embed = discord.Embed(
                title="📋 Your Order History",
                color=self.embeds.COLORS['primary'],
                timestamp=discord.utils.utcnow()
            )
            
            if not orders:
                embed.add_field(
                    name="No Orders Yet",
                    value="You haven't made any orders yet. Start trading to build your history!",
                    inline=False
                )
            else:
                # Group orders by status
                status_groups = {}
                for order in orders:
                    status = order['status']
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(order)
                
                # Display each status group
                status_emojis = {
                    'completed': '✅ Completed',
                    'confirmed': '🤝 Confirmed', 
                    'pending': '⏳ Pending',
                    'cancelled': '❌ Cancelled'
                }
                
                for status, status_orders in status_groups.items():
                    if len(status_orders) == 0:
                        continue
                    
                    orders_text = ""
                    for order in status_orders[:5]:  # Limit to 5 per status
                        other_party = order['other_party_name'] or "Unknown User"
                        order_type = "Bought from" if order['listing_type'] == 'WTS' else "Sold to"
                        
                        orders_text += (
                            f"**#{order['id']}** {order_type} {other_party}\n"
                            f"📦 {order['item']} • <t:{int(order['created_at'].timestamp())}:R>\n\n"
                        )
                    
                    if orders_text:
                        embed.add_field(
                            name=status_emojis.get(status, status.title()),
                            value=orders_text,
                            inline=False
                        )
            
            embed.set_footer(text="Showing your most recent orders")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing orders: {e}")
            await interaction.response.send_message(
                "An error occurred while loading your orders.", ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(ScoringCommands(bot))
