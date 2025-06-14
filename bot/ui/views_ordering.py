"""
Discord UI Views for the ordering system.
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone
from typing import Optional
import asyncio

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

            ordering_service = self.bot.ordering_service

            result = await ordering_service.handle_order_confirmation(
                self.order_id, interaction.user.id, True
            )

            if result == "both_confirmed":
                # Both parties confirmed - show completion message
                embed = discord.Embed(
                    title="🎉 Trade Confirmed!",
                    description="Both parties have confirmed the trade! Please check your DMs for rating and completion instructions.",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)
                logger.info(f"✅ BUTTON DEBUG: Both parties confirmed trade {self.order_id}")

            elif result == "waiting":
                # Only this user confirmed - show waiting message
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

            ordering_service = self.bot.ordering_service

            result = await ordering_service.handle_order_confirmation(
                self.order_id, interaction.user.id, False
            )

            if result:
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

    @discord.ui.button(label="⭐ 1 Star", style=discord.ButtonStyle.danger, row=0)
    async def rate_1_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 1 star."""
        await self.handle_rating(interaction, 1)

    @discord.ui.button(label="⭐⭐ 2 Stars", style=discord.ButtonStyle.danger, row=0)
    async def rate_2_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 2 stars."""
        await self.handle_rating(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐ 3 Stars", style=discord.ButtonStyle.secondary, row=0)
    async def rate_3_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 3 stars."""
        await self.handle_rating(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐ 4 Stars", style=discord.ButtonStyle.success, row=1)
    async def rate_4_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 4 stars."""
        await self.handle_rating(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐ 5 Stars", style=discord.ButtonStyle.success, row=1)
    async def rate_5_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 5 stars."""
        await self.handle_rating(interaction, 5)

    async def handle_rating(self, interaction: discord.Interaction, rating: int):
        """Handle star rating selection."""
        try:
            # Open modal for optional comment
            modal = QuickRatingModal(self.bot, self.order_id, self.other_party_id, rating)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error handling rating: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass

class QuickRatingModal(discord.ui.Modal):
    """Modal for submitting ratings with pre-selected stars."""

    def __init__(self, bot, order_id: str, rated_user_id: int, rating: int):
        stars = "⭐" * rating
        super().__init__(title=f"Rate {rating}/5 Stars")
        self.bot = bot
        self.order_id = order_id
        self.rated_user_id = rated_user_id
        self.rating = rating

        # Comment input
        self.comment_input = discord.ui.TextInput(
            label=f"Comment for {stars} rating (optional)",
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
            comment = self.comment_input.value.strip()

            await interaction.response.defer()

            ordering_service = self.bot.ordering_service

            success = await ordering_service.handle_rating_submission(
                self.order_id, interaction.user.id, self.rated_user_id, self.rating, comment
            )

            if success:
                stars = "⭐" * self.rating
                if self.rating < 3:
                    await interaction.followup.send(
                        f"⚠️ Your {stars} rating has been submitted for admin review due to the low score.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"✅ Thank you for your {stars} rating! It has been recorded.",
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

            ordering_service = self.bot.ordering_service

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

            ordering_service = self.bot.ordering_service

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

            ordering_service = self.bot.ordering_service

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

class EventConfirmationView(discord.ui.View):
    """View for event participation confirmation."""

    def __init__(self, bot, event_id: int, role: str, user_id: int):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.bot = bot
        self.event_id = event_id
        self.role = role
        self.user_id = user_id

    @discord.ui.button(label="✅ Confirm Participation", style=discord.ButtonStyle.green)
    async def confirm_participation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle participation confirmation."""
        try:
            await interaction.response.defer()

            # Store confirmation in database
            success = await self.store_event_confirmation(interaction.user.id, True)

            if success:
                embed = discord.Embed(
                    title="✅ Participation Confirmed",
                    description="You have confirmed your participation in this event. Please wait for other participants.",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)

            else:
                await interaction.followup.send("❌ Failed to confirm participation. Please try again.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error confirming participation: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Decline Participation", style=discord.ButtonStyle.red)
    async def decline_participation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle participation decline."""
        try:
            await interaction.response.defer()

            # Store decline in database
            success = await self.store_event_confirmation(interaction.user.id, False)

            if success:
                embed = discord.Embed(
                    title="❌ Participation Declined",
                    description="You have declined to participate in this event.",
                    color=0xFF0000,
                    timestamp=datetime.now(timezone.utc)
                )

                # Disable buttons
                for item in self.children:
                    item.disabled = True

                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.followup.send("❌ Failed to decline participation. Please try again.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error declining participation: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    async def store_event_confirmation(self, user_id: int, confirmed: bool) -> bool:
        """Store event confirmation in database."""
        try:
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO event_confirmations (event_id, user_id, role, confirmed, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (event_id, user_id) 
                DO UPDATE SET confirmed = $4, created_at = $5
                """,
                self.event_id, user_id, self.role, confirmed, datetime.now(timezone.utc)
            )
            
            # Check if we should schedule rating prompts (when both seller and at least one buyer confirm)
            if confirmed:
                await self.check_and_schedule_rating_prompt()
            
            return True
        except Exception as e:
            logger.error(f"Error storing event confirmation: {e}")
            return False

    async def check_and_schedule_rating_prompt(self):
        """Check if rating prompt should be scheduled and schedule it."""
        try:
            # Get all confirmations for this event
            confirmations = await self.bot.db_manager.execute_query(
                """
                SELECT user_id, role, confirmed FROM event_confirmations 
                WHERE event_id = $1 AND confirmed = TRUE
                """,
                self.event_id
            )
            
            seller_confirmed = any(c['role'] == 'seller' and c['confirmed'] for c in confirmations)
            buyer_confirmed = any(c['role'] == 'buyer' and c['confirmed'] for c in confirmations)
            
            # If both seller and at least one buyer confirmed, schedule rating prompt
            if seller_confirmed and buyer_confirmed:
                logger.info(f"Both parties confirmed for event {self.event_id}, scheduling rating prompt")
                scheduler_service = self.bot.scheduler_service
                asyncio.create_task(scheduler_service.schedule_rating_prompt(self.event_id, 10))
                
        except Exception as e:
            logger.error(f"Error checking rating prompt schedule: {e}")

class EventRatingView(discord.ui.View):
    """View for rating event seller."""

    def __init__(self, bot, event_id: int, seller_id: int):
        super().__init__(timeout=7200)  # 2 hour timeout
        self.bot = bot
        self.event_id = event_id
        self.seller_id = seller_id

    @discord.ui.button(label="⭐ 1 Star", style=discord.ButtonStyle.danger, row=0)
    async def rate_1_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 1)

    @discord.ui.button(label="⭐⭐ 2 Stars", style=discord.ButtonStyle.danger, row=0)
    async def rate_2_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐ 3 Stars", style=discord.ButtonStyle.secondary, row=0)
    async def rate_3_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐ 4 Stars", style=discord.ButtonStyle.success, row=1)
    async def rate_4_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐ 5 Stars", style=discord.ButtonStyle.success, row=1)
    async def rate_5_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 5)

    async def handle_rating(self, interaction: discord.Interaction, rating: int):
        """Handle star rating selection."""
        try:
            # Open modal for optional comment
            modal = EventRatingModal(self.bot, self.event_id, self.seller_id, rating)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error handling event rating: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass

class EventRatingModal(discord.ui.Modal):
    """Modal for submitting event ratings."""

    def __init__(self, bot, event_id: int, seller_id: int, rating: int):
        stars = "⭐" * rating
        super().__init__(title=f"Rate {rating}/5 Stars")
        self.bot = bot
        self.event_id = event_id
        self.seller_id = seller_id
        self.rating = rating

        # Comment input
        self.comment_input = discord.ui.TextInput(
            label=f"Comment for {stars} rating (optional)",
            placeholder="Share your experience with this seller...",
            style=discord.TextStyle.paragraph,
            min_length=0,
            max_length=500,
            required=False
        )
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle rating submission."""
        try:
            comment = self.comment_input.value.strip()

            await interaction.response.defer()

            # Store rating in database
            success = await self.bot.db_manager.execute_command(
                """
                INSERT INTO event_ratings (event_id, rater_id, seller_id, rating, comment, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (event_id, rater_id) DO NOTHING
                """,
                self.event_id, interaction.user.id, self.seller_id, self.rating, comment, datetime.now(timezone.utc)
            )

            if success:
                # Update seller's reputation
                await self.bot.db_manager.add_reputation(
                    interaction.user.id, self.seller_id, None, self.rating, comment
                )

                # Check if all ratings are complete and send summary
                scheduler_service = self.bot.scheduler_service
                await scheduler_service.check_ratings_complete_and_send_summary(self.event_id)

                stars = "⭐" * self.rating
                if self.rating < 3:
                    await interaction.followup.send(
                        f"⚠️ Your {stars} rating has been submitted for admin review due to the low score.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"✅ Thank you for your {stars} rating! It has been recorded.",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "❌ You have already rated this event or an error occurred.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error submitting event rating: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

class TradeRatingView(discord.ui.View):
    """View for trade rating buttons."""

    def __init__(self, bot, order_id: str, disabled_users: set = None):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.bot = bot
        self.order_id = order_id
        self.disabled_users = disabled_users or set()

        # Disable buttons if user has already rated
        if self.disabled_users:
            self.disable_buttons_for_users(self.disabled_users)

    def disable_buttons_for_user(self, user_id: int):
        """Disable buttons for a specific user."""
        self.disabled_users.add(user_id)
        self.disable_buttons_for_users({user_id})

    def disable_buttons_for_users(self, user_ids: set):
        """Disable buttons for specific users."""
        # This will be checked in the button interactions
        pass

    @discord.ui.button(label="1⭐", style=discord.ButtonStyle.danger, emoji="1️⃣")
    async def rate_1_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 1 star."""
        if interaction.user.id in self.disabled_users:
            await interaction.response.send_message("❌ You have already rated this trade.", ephemeral=True)
            return
        await self.handle_rating(interaction, 1)

    @discord.ui.button(label="2⭐", style=discord.ButtonStyle.danger, emoji="2️⃣")
    async def rate_2_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 2 stars."""
        if interaction.user.id in self.disabled_users:
            await interaction.response.send_message("❌ You have already rated this trade.", ephemeral=True)
            return
        await self.handle_rating(interaction, 2)

    @discord.ui.button(label="3⭐", style=discord.ButtonStyle.secondary, emoji="3️⃣")
    async def rate_3_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 3 stars."""
        if interaction.user.id in self.disabled_users:
            await interaction.response.send_message("❌ You have already rated this trade.", ephemeral=True)
            return
        await self.handle_rating(interaction, 3)

    @discord.ui.button(label="4⭐", style=discord.ButtonStyle.success, emoji="4️⃣")
    async def rate_4_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 4 stars."""
        if interaction.user.id in self.disabled_users:
            await interaction.response.send_message("❌ You have already rated this trade.", ephemeral=True)
            return
        await self.handle_rating(interaction, 4)

    @discord.ui.button(label="5⭐", style=discord.ButtonStyle.success, emoji="5️⃣")
    async def rate_5_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rate 5 stars."""
        if interaction.user.id in self.disabled_users:
            await interaction.response.send_message("❌ You have already rated this trade.", ephemeral=True)
            return
        await self.handle_rating(interaction, 5)

    async def handle_rating(self, interaction: discord.Interaction, rating: int):
        """Handle rating submission."""
        try:
            user_id = interaction.user.id
            order_data = self.bot.ordering_service.pending_ratings.get(self.order_id)

            if not order_data:
                await interaction.response.send_message(
                    "❌ This rating request has expired or is invalid.", ephemeral=True
                )
                return

            # Check if user already rated
            user_ratings = order_data.get('ratings', {})
            if user_id in user_ratings:
                await interaction.response.send_message(
                    "❌ You have already rated this trade.", ephemeral=True
                )
                return

            # Determine who they're rating
            if user_id == order_data['buyer_id']:
                rated_user_id = order_data['seller_id']
                rated_username = order_data['seller_username']
            elif user_id == order_data['seller_id']:
                rated_user_id = order_data['buyer_id']
                rated_username = order_data['buyer_username']
            else:
                await interaction.response.send_message(
                    "❌ You are not authorized to rate this trade.", ephemeral=True
                )
                return

            # Open modal for optional comment
            modal = QuickRatingModal(self.bot, self.order_id, rated_user_id, rating)
            await interaction.response.send_modal(modal)

# Open modal for optional comment
            modal = QuickRatingModal(self.bot, self.order_id, rated_user_id, rating)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error handling rating: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass