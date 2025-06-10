"""
UI views for the ordering system.
"""

import discord
from discord.ext import commands
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class OrderConfirmationView(discord.ui.View):
    """View for confirming orders."""

    def __init__(self, bot, order_id: int, user_type: str):
        super().__init__(timeout=86400)  # 24 hours
        self.bot = bot
        self.order_id = order_id
        self.user_type = user_type

    @discord.ui.button(label="Confirm Order", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the order."""
        try:
            from bot.services.ordering import OrderingService
            ordering_service = OrderingService(self.bot)

            success = await ordering_service.confirm_order(
                self.order_id, interaction.user.id, self.user_type
            )

            if success:
                embed = discord.Embed(
                    title="✅ Order Confirmed",
                    description="You have confirmed this order. Waiting for the other party to confirm.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not confirm order. It may have been cancelled or expired.",
                    color=0xff0000
                )

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error confirming order: {e}")
            await interaction.response.send_message(
                "An error occurred while confirming the order.", ephemeral=True
            )

    @discord.ui.button(label="Cancel Order", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the order."""
        try:
            from bot.services.ordering import OrderingService
            ordering_service = OrderingService(self.bot)

            success = await ordering_service.cancel_order(
                self.order_id, interaction.user.id, "Cancelled by user"
            )

            if success:
                embed = discord.Embed(
                    title="❌ Order Cancelled",
                    description="You have cancelled this order.",
                    color=0xff0000
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not cancel order.",
                    color=0xff0000
                )

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            await interaction.response.send_message(
                "An error occurred while cancelling the order.", ephemeral=True
            )

class OrderCompletionView(discord.ui.View):
    """View for completing orders."""

    def __init__(self, bot, order_id: int, user_type: str):
        super().__init__(timeout=604800)  # 7 days
        self.bot = bot
        self.order_id = order_id
        self.user_type = user_type

    @discord.ui.button(label="Complete Order", style=discord.ButtonStyle.green, emoji="🎯")
    async def complete_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mark order as completed."""
        try:
            from bot.services.ordering import OrderingService
            ordering_service = OrderingService(self.bot)

            success = await ordering_service.complete_order(
                self.order_id, interaction.user.id, self.user_type
            )

            if success:
                embed = discord.Embed(
                    title="🎉 Order Completed!",
                    description="Order has been marked as completed. You should receive a rating request shortly.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not complete order. Make sure both parties have confirmed it.",
                    color=0xff0000
                )

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error completing order: {e}")
            await interaction.response.send_message(
                "An error occurred while completing the order.", ephemeral=True
            )

class RatingView(discord.ui.View):
    """View for rating trading partners."""

    def __init__(self, bot, order_id: int, target_user_id: int):
        super().__init__(timeout=604800)  # 7 days
        self.bot = bot
        self.order_id = order_id
        self.target_user_id = target_user_id

    @discord.ui.button(label="1⭐", style=discord.ButtonStyle.red)
    async def rate_1_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_rating_modal(interaction, 1)

    @discord.ui.button(label="2⭐", style=discord.ButtonStyle.red)
    async def rate_2_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_rating_modal(interaction, 2)

    @discord.ui.button(label="3⭐", style=discord.ButtonStyle.gray)
    async def rate_3_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_rating_modal(interaction, 3)

    @discord.ui.button(label="4⭐", style=discord.ButtonStyle.green)
    async def rate_4_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_rating_modal(interaction, 4)

    @discord.ui.button(label="5⭐", style=discord.ButtonStyle.green)
    async def rate_5_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_rating_modal(interaction, 5)

    async def show_rating_modal(self, interaction: discord.Interaction, rating: int):
        """Show modal for rating comment."""
        modal = RatingModal(self.bot, self.order_id, self.target_user_id, rating)
        await interaction.response.send_modal(modal)

class RatingModal(discord.ui.Modal):
    """Modal for rating with comment."""

    def __init__(self, bot, order_id: int, target_user_id: int, rating: int):
        super().__init__(title=f"Rate {rating} Star{'s' if rating != 1 else ''}")
        self.bot = bot
        self.order_id = order_id
        self.target_user_id = target_user_id
        self.rating = rating

    comment = discord.ui.TextInput(
        label="Comment (Optional)",
        placeholder="Share your experience with this trader...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            from bot.services.reputation import ReputationService
            reputation_service = ReputationService(self.bot)

            success = await reputation_service.add_rating(
                interaction.user.id,
                self.target_user_id,
                self.order_id,
                self.rating,
                self.comment.value or ""
            )

            if success:
                stars = "⭐" * self.rating
                embed = discord.Embed(
                    title="✅ Rating Submitted",
                    description=f"You rated your trading partner {stars} ({self.rating}/5 stars).",
                    color=0x00ff00
                )
                if self.comment.value:
                    embed.add_field(
                        name="Your Comment",
                        value=self.comment.value,
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not submit rating. You may have already rated this trader for this order.",
                    color=0xff0000
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error submitting rating: {e}")
            await interaction.response.send_message(
                "An error occurred while submitting your rating.", ephemeral=True
            )

class MatchSelectionView(discord.ui.View):
    """View for selecting matches from queue results."""

    def __init__(self, bot, user_id: int, matches: List[Dict[str, Any]], listing_type: str):
        super().__init__(timeout=600)  # 10 minutes
        self.bot = bot
        self.user_id = user_id
        self.matches = matches
        self.listing_type = listing_type

        # Add select menu for matches
        if matches:
            self.add_item(MatchSelect(matches))

    async def create_order_with_selected_match(self, interaction: discord.Interaction, selected_listing_id: int):
        """Create order with selected match."""
        try:
            # Find the selected match
            selected_match = None
            for match in self.matches:
                if match['id'] == selected_listing_id:
                    selected_match = match
                    break

            if not selected_match:
                await interaction.response.send_message("Selected listing not found.", ephemeral=True)
                return

            # Determine buyer and seller based on listing type
            if self.listing_type == "WTS":  # User is selling, match is buyer
                buyer_id = selected_match['user_id']
                seller_id = self.user_id
            else:  # User is buying, match is seller
                buyer_id = self.user_id
                seller_id = selected_match['user_id']

            # Create order
            from bot.services.ordering import OrderingService
            ordering_service = OrderingService(self.bot)

            order_id = await ordering_service.create_order(
                buyer_id, seller_id, selected_listing_id, interaction.guild.id
            )

            if order_id:
                embed = discord.Embed(
                    title="🎯 Order Created!",
                    description=f"Order #{order_id} has been created with your selected match.",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Next Steps",
                    value="Both parties will receive confirmation requests. Check your DMs!",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not create order with selected match.",
                    color=0xff0000
                )

            # Disable view
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error creating order with match: {e}")
            await interaction.response.send_message(
                "An error occurred while creating the order.", ephemeral=True
            )

class QueueNotificationView(discord.ui.View):
    """View for queue notifications with match results."""

    def __init__(self, bot, user_id: int, matches: List[Dict[str, Any]], listing_type: str):
        super().__init__(timeout=600)  # 10 minutes
        self.bot = bot
        self.user_id = user_id
        self.matches = matches
        self.listing_type = listing_type

    @discord.ui.button(label="View Matches", style=discord.ButtonStyle.green, emoji="👀")
    async def view_matches(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed match selection."""
        try:
            # Create match selection view
            view = MatchSelectionView(self.bot, self.user_id, self.matches, self.listing_type)
            
            embed = discord.Embed(
                title="🎯 Select Your Match",
                description=f"Choose from {len(self.matches)} available matches:",
                color=0x00ff00
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error showing matches: {e}")
            await interaction.response.send_message(
                "An error occurred while loading matches.", ephemeral=True
            )

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.gray, emoji="❌")
    async def dismiss_notification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Dismiss the notification."""
        try:
            embed = discord.Embed(
                title="📝 Notification Dismissed",
                description="Match notification has been dismissed.",
                color=0x808080
            )

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Error dismissing notification: {e}")
            await interaction.response.send_message(
                "An error occurred.", ephemeral=True
            )

class MatchSelect(discord.ui.Select):
    """Select dropdown for choosing matches."""

    def __init__(self, matches: List[Dict[str, Any]]):
        options = []

        for i, match in enumerate(matches[:25]):  # Discord limit of 25 options
            user_name = match.get('username', f"User {match['user_id']}")
            reputation = f"⭐{match['reputation_avg']:.1f}" if match.get('reputation_count', 0) > 0 else "New"

            # Create option description
            description = f"{match['item']} (Qty: {match['quantity']}) • {reputation}"
            if len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=f"{user_name}",
                description=description,
                value=str(match['id']),
                emoji="🤝"
            ))

        super().__init__(
            placeholder="Choose a trader to create an order with...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_listing_id = int(self.values[0])
        await self.view.create_order_with_selected_match(interaction, selected_listing_id)