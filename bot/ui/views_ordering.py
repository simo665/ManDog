"""
Discord UI Views for the ordering system.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class OrderConfirmationView(discord.ui.View):
    """View for order confirmation."""

    def __init__(self, bot, order_id: str, role: str):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.bot = bot
        self.order_id = order_id
        self.role = role

    @discord.ui.button(label="✅ Confirm Trade", style=discord.ButtonStyle.green)
    async def confirm_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle trade confirmation."""
        try:
            await interaction.response.defer()

            ordering_service = self.bot.get_cog('OrderingService')
            if not ordering_service:
                from bot.services.ordering import OrderingService
                ordering_service = OrderingService(self.bot)

            success = await ordering_service.handle_order_confirmation(
                self.order_id, interaction.user.id, True
            )

            if success:
                # Update the message
                embed = discord.Embed(
                    title="✅ Trade Confirmed",
                    description="You have confirmed this trade. Waiting for the other party to confirm.",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)
                logger.info(f"✅ BUTTON DEBUG: Successfully confirmed trade {self.order_id}")
            else:
                logger.error(f"❌ BUTTON DEBUG: Failed to confirm trade {self.order_id}")
                await interaction.followup.send("❌ Failed to confirm trade - order may have expired", ephemeral=True)

        except Exception as e:
            logger.error(f"Error confirming trade: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Decline Trade", style=discord.ButtonStyle.red)
    async def decline_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle trade decline."""
        try:
            await interaction.response.defer()

            ordering_service = self.bot.get_cog('OrderingService')
            if not ordering_service:
                from bot.services.ordering import OrderingService
                ordering_service = OrderingService(self.bot)

            success = await ordering_service.handle_order_confirmation(
                self.order_id, interaction.user.id, False
            )

            if success:
                # Update the message
                embed = discord.Embed(
                    title="❌ Trade Declined",
                    description="You have declined this trade. The other party has been notified.",
                    color=0xFF0000,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)
                logger.info(f"✅ BUTTON DEBUG: Successfully declined trade {self.order_id}")
            else:
                logger.error(f"❌ BUTTON DEBUG: Failed to decline trade {self.order_id}")
                await interaction.followup.send("❌ Failed to decline trade - it may have already been processed", ephemeral=True)

        except Exception as e:
            logger.error(f"Error declining trade: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

class OrderCompletionView(discord.ui.View):
    """View for order completion and rating."""

    def __init__(self, bot, order_id: str, role: str, other_party_id: int):
        super().__init__(timeout=7200)  # 2 hour timeout
        self.bot = bot
        self.order_id = order_id
        self.role = role
        self.other_party_id = other_party_id

    @discord.ui.button(label="⭐ Rate Trade Partner", style=discord.ButtonStyle.primary)
    async def rate_partner(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open rating modal."""
        try:
            modal = RatingModal(self.bot, self.order_id, self.other_party_id)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error opening rating modal: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass

class RatingModal(discord.ui.Modal):
    """Modal for submitting ratings."""

    def __init__(self, bot, order_id: str, rated_user_id: int):
        super().__init__(title="Rate Your Trade Partner")
        self.bot = bot
        self.order_id = order_id
        self.rated_user_id = rated_user_id

        # Rating input
        self.rating_input = discord.ui.TextInput(
            label="Rating (1-5)",
            placeholder="Enter a rating from 1 to 5",
            min_length=1,
            max_length=1,
            required=True
        )
        self.add_item(self.rating_input)

        # Comment input
        self.comment_input = discord.ui.TextInput(
            label="Comment (optional)",
            placeholder="Share your experience with this trader...",
            style=discord.TextStyle.paragraph,
            min_length=0,
            max_length=500,
            required=False
        )
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle rating submission."""
        try:
            # Validate rating
            try:
                rating = int(self.rating_input.value)
                if rating < 1 or rating > 5:
                    raise ValueError("Rating out of range")
            except ValueError:
                await interaction.response.send_message(
                    "❌ Please enter a valid rating between 1 and 5",
                    ephemeral=True
                )
                return

            comment = self.comment_input.value.strip()

            await interaction.response.defer()

            ordering_service = self.bot.get_cog('OrderingService')
            if not ordering_service:
                from bot.services.ordering import OrderingService
                ordering_service = OrderingService(self.bot)

            success = await ordering_service.handle_rating_submission(
                self.order_id, interaction.user.id, self.rated_user_id, rating, comment
            )

            if success:
                if rating < 3:
                    await interaction.followup.send(
                        "⚠️ Your rating has been submitted for admin review due to the low score.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "✅ Thank you for your rating! It has been recorded.",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "❌ Failed to submit rating. Please try again.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error submitting rating: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

class RatingModerationView(discord.ui.View):
    """View for admin rating moderation."""

    def __init__(self, bot, order_id: str, rater_id: int, rated_id: int, rating: int, comment: str):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.order_id = order_id
        self.rater_id = rater_id
        self.rated_id = rated_id
        self.rating = rating
        self.comment = comment

    @discord.ui.button(label="✅ Approve Rating", style=discord.ButtonStyle.green)
    async def approve_rating(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve the rating."""
        try:
            await interaction.response.defer()

            ordering_service = self.bot.get_cog('OrderingService')
            if not ordering_service:
                from bot.services.ordering import OrderingService
                ordering_service = OrderingService(self.bot)

            success = await ordering_service.handle_admin_rating_decision(
                self.order_id, self.rater_id, self.rated_id, 
                self.rating, self.comment, True, interaction.user.id
            )

            if success:
                # Update embed
                embed = discord.Embed(
                    title="✅ Rating Approved",
                    description=f"Rating approved by {interaction.user.mention}",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)

                # Archive the channel after 5 minutes
                await interaction.followup.send("This channel will be archived in 5 minutes.")
                import asyncio
                await asyncio.sleep(300)
                await interaction.channel.delete(reason="Rating moderation completed")

        except Exception as e:
            logger.error(f"Error approving rating: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Reject Rating", style=discord.ButtonStyle.red)
    async def reject_rating(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reject the rating."""
        try:
            await interaction.response.defer()

            ordering_service = self.bot.get_cog('OrderingService')
            if not ordering_service:
                from bot.services.ordering import OrderingService
                ordering_service = OrderingService(self.bot)

            success = await ordering_service.handle_admin_rating_decision(
                self.order_id, self.rater_id, self.rated_id, 
                self.rating, self.comment, False, interaction.user.id
            )

            if success:
                # Update embed
                embed = discord.Embed(
                    title="❌ Rating Rejected",
                    description=f"Rating rejected by {interaction.user.mention}",
                    color=0xFF0000,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)

                # Archive the channel after 5 minutes
                await interaction.followup.send("This channel will be archived in 5 minutes.")
                import asyncio
                await asyncio.sleep(300)
                await interaction.channel.delete(reason="Rating moderation completed")

        except Exception as e:
            logger.error(f"Error rejecting rating: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

# Legacy views for compatibility
class MatchSelectionView(discord.ui.View):
    """Legacy compatibility view."""
    def __init__(self, bot, matches):
        super().__init__(timeout=300)
        self.bot = bot

class QueueNotificationView(discord.ui.View):
    """Legacy compatibility view."""
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot

class RatingView(discord.ui.View):
    """Legacy compatibility view."""
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot