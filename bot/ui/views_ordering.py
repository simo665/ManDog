import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone
from typing import Optional
import asyncio
import traceback
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class QuickRatingModal(discord.ui.Modal):
    """Modal for submitting ratings with pre-selected stars."""

    def __init__(self, bot, order_id: str, rated_user_id: int, rating: int, is_event_rating: bool = False, rating_interaction: discord.Interaction = None, rating_view = None):
        stars = "⭐" * rating
        super().__init__(title=f"Rate {rating}/5 Stars")
        self.bot = bot
        self.order_id = order_id
        self.rated_user_id = rated_user_id
        self.rating = rating
        self.is_event_rating = is_event_rating
        self.rating_interaction = rating_interaction
        self.rating_view = rating_view

        # Comment input
        label_text = f"Comment for {stars} rating (Required)"
        placeholder_text = "Share your experience with this seller..." if is_event_rating else "Share your experience with this trader..."

        self.comment_input = discord.ui.TextInput(
            label=label_text,
            placeholder=placeholder_text,
            style=discord.TextStyle.paragraph,
            min_length=10,
            max_length=500,
            required=True
        )
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle rating submission."""
        try:
            comment = self.comment_input.value.strip()

            await interaction.response.defer()

            if self.is_event_rating:
                
                # Handle event rating (order_id is actually event_id)
                event_id = int(self.order_id)
                # Get event data to get guild_id
                event_data = await self.bot.db_manager.execute_query(
                    """
                    SELECT se.*, l.item, l.zone, l.guild_id
                    FROM scheduled_events se
                    JOIN listings l ON se.listing_id = l.id
                    WHERE se.id = $1
                    """,
                    event_id
                )

                if not event_data:
                    logger.error(f"Event {event_id} not found")
                    await interaction.followup.send("❌ Event not found.", ephemeral=True)
                    return

                guild_id = event_data[0]['guild_id']

                # Get guild rating configuration
                rating_config = await self.bot.db_manager.execute_query(
                    "SELECT admin_channel_id, low_rating_threshold FROM guild_rating_configs WHERE guild_id = $1",
                    guild_id
                )

                threshold = 3  # default threshold
                admin_channel_id = None
                if rating_config:
                    threshold = rating_config[0]['low_rating_threshold'] or 3
                    admin_channel_id = rating_config[0]['admin_channel_id']
                
                if self.rating_interaction and self.rating_view:
                    for item in self.rating_view.children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True
                    await self.rating_interaction.message.edit(view=self.rating_view)
                    
                # Check if rating needs admin approval
                if self.rating < threshold and admin_channel_id:
                    # Send for admin approval
                    await self.send_event_rating_for_approval(interaction, comment, admin_channel_id, event_id)
                    await interaction.followup.send(
                        f"⚠️ Your {self.rating}⭐ rating has been submitted for admin review due to the low score.",
                        ephemeral=True
                    )
                    return

                # Good rating or no admin config - save immediately
                success = await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO event_ratings (event_id, rater_id, seller_id, rating, comment, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (event_id, rater_id) DO NOTHING
                    """,
                    event_id, interaction.user.id, self.rated_user_id, self.rating, comment, datetime.now(timezone.utc)
                )

                if success:
                    # Update seller's reputation manually for event ratings
                    await self.update_seller_reputation()

                    stars = "⭐" * self.rating
                    await interaction.followup.send(
                        f"✅ Thank you for your {stars} rating! It has been recorded.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ You have already rated this event or an error occurred.",
                        ephemeral=True
                    )
            else:
                # Handle trade order rating
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
                        "❌ Failed to submit rating.",
                        ephemeral=True
                    )

        except Exception as e:
            logger.error(f"Error submitting rating: {traceback.format_exc()}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    async def send_event_rating_for_approval(self, interaction: discord.Interaction, comment: str, admin_channel_id: int, event_id: int):
        """Send event rating to admin channel for approval."""
        try:
            # Get event details first to get guild_id
            event_data = await self.bot.db_manager.execute_query(
                """
                SELECT se.*, l.item, l.zone, l.guild_id
                FROM scheduled_events se
                JOIN listings l ON se.listing_id = l.id
                WHERE se.id = $1
                """,
                event_id
            )

            if not event_data:
                logger.error(f"Event {event_id} not found")
                return

            event = event_data[0]

            # Get guild from bot using guild_id from event data
            guild = self.bot.get_guild(event['guild_id'])
            if not guild:
                logger.error(f"Guild {event['guild_id']} not found")
                return

            admin_channel = guild.get_channel(admin_channel_id)
            if not admin_channel:
                logger.error(f"Admin channel {admin_channel_id} not found")
                return

            seller = guild.get_member(self.rated_user_id)
            rater = interaction.user

            # Create moderation embed
            embed = discord.Embed(
                title="⚠️ Rating Requires Moderation",
                description="A low rating has been submitted and requires admin approval.",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="🎯 Item", value=event['item'], inline=True)
            embed.add_field(name="📍 Zone", value=event['zone'], inline=True)
            embed.add_field(name="⭐ Rating", value=f"{self.rating}/5", inline=True)
            embed.add_field(name="👤 Rater", value=rater.mention, inline=True)
            embed.add_field(name="👥 Seller", value=seller.mention if seller else f"User {self.rated_user_id}", inline=True)
            embed.add_field(name="📝 Comment", value=comment or "No comment provided", inline=False)

            # Create approval view
            view = EventRatingModerationView(
                self.bot, event_id, interaction.user.id, self.rated_user_id, 
                self.rating, comment
            )

            await admin_channel.send(
                content="🚨 **Rating Moderation Required**",
                embed=embed,
                view=view
            )

            logger.info(f"Sent event rating moderation request to {admin_channel.name} for event {event_id}")

        except Exception as e:
            logger.error(f"Error sending event rating for approval: {e}")

    async def update_seller_reputation(self):
        """Update seller's reputation after rating submission."""
        try:
            # Get all ratings for this seller
            ratings = await self.bot.db_manager.execute_query(
                "SELECT rating FROM event_ratings WHERE seller_id = $1",
                self.rated_user_id
            )

            if ratings:
                total_ratings = len(ratings)
                avg_rating = sum(r['rating'] for r in ratings) / total_ratings

                # Update user reputation
                await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO users (user_id, reputation_avg, reputation_count, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        reputation_avg = $2,
                        reputation_count = $3,
                        updated_at = $4
                    """,
                    self.rated_user_id, avg_rating, total_ratings, datetime.now(timezone.utc)
                )

        except Exception as e:
            logger.error(f"Error updating seller reputation: {e}")

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
                asyncio.create_task(scheduler_service.schedule_rating_prompt(self.event_id, int(os.getenv("rating_delay_seconds", 3600))))

        except Exception as e:
            logger.error(f"Error checking rating prompt schedule: {e}")

class EventRatingView(discord.ui.View):
    """View for rating event seller."""

    def __init__(self, bot, event_id: int, seller_id: int):
        super().__init__(timeout=7200)  # 2 hour timeout
        self.bot = bot
        self.event_id = event_id
        self.seller_id = seller_id

    @discord.ui.button(label="1 Star", style=discord.ButtonStyle.danger, row=0, emoji="⭐")
    async def rate_1_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 1)

    @discord.ui.button(label="2 Stars", style=discord.ButtonStyle.danger, row=0, emoji="⭐")
    async def rate_2_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 2)

    @discord.ui.button(label="3 Stars", style=discord.ButtonStyle.secondary, row=0, emoji="⭐")
    async def rate_3_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 3)

    @discord.ui.button(label="4 Stars", style=discord.ButtonStyle.success, row=1, emoji="⭐")
    async def rate_4_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 4)

    @discord.ui.button(label="5 Stars", style=discord.ButtonStyle.success, row=1, emoji="⭐")
    async def rate_5_stars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rating(interaction, 5)

    async def handle_rating(self, interaction: discord.Interaction, rating: int):
        try:
            modal = QuickRatingModal(self.bot, str(self.event_id), self.seller_id, rating, is_event_rating=True, rating_interaction=interaction, rating_view = self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error handling event rating: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred", ephemeral=True)
            except:
                pass

class EventRatingModerationView(discord.ui.View):
    """View for admin event rating moderation."""

    def __init__(self, bot, event_id: int, rater_id: int, seller_id: int, rating: int, comment: str):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.event_id = event_id
        self.rater_id = rater_id
        self.seller_id = seller_id
        self.rating = rating
        self.comment = comment

    @discord.ui.button(label="✅ Approve Rating", style=discord.ButtonStyle.green)
    async def approve_rating(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve the rating."""
        try:
            await interaction.response.defer()

            # Save the approved rating
            success = await self.bot.db_manager.execute_command(
                """
                INSERT INTO event_ratings (event_id, rater_id, seller_id, rating, comment, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (event_id, rater_id) DO NOTHING
                """,
                self.event_id, self.rater_id, self.seller_id, self.rating, self.comment, datetime.now(timezone.utc)
            )

            if success:
                # Update user reputation
                await self.update_seller_reputation()

                # Update embed to show approval
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

                logger.info(f"Admin {interaction.user.id} approved rating for event {self.event_id}")

        except Exception as e:
            logger.error(f"Error approving event rating: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Reject Rating", style=discord.ButtonStyle.red)
    async def reject_rating(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reject the rating."""
        try:
            await interaction.response.defer()

            # Update embed to show rejection
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

            logger.info(f"Admin {interaction.user.id} rejected rating for event {self.event_id}")

        except Exception as e:
            logger.error(f"Error rejecting event rating: {e}")
            try:
                await interaction.followup.send("❌ An error occurred", ephemeral=True)
            except:
                pass

    async def update_seller_reputation(self):
        """Update seller's reputation after approved rating."""
        try:
            # Get all ratings for this seller
            ratings = await self.bot.db_manager.execute_query(
                "SELECT rating FROM event_ratings WHERE seller_id = $1",
                self.seller_id
            )

            if ratings:
                total_ratings = len(ratings)
                avg_rating = sum(r['rating'] for r in ratings) / total_ratings

                # Update user reputation
                await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO users (user_id, reputation_avg, reputation_count, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id)
                    DO UPDATE SET                        reputation_avg = $2,
                        reputation_count = $3,
                        updated_at = $4
                    """,
                    self.seller_id, avg_rating, total_ratings, datetime.now(timezone.utc)
                )

        except Exception as e:
            logger.error(f"Error updating seller reputation: {e}")