"""
Ordering system service for managing transactions and queue matching.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import asyncio

from bot.ui.embeds import MarketplaceEmbeds

logger = logging.getLogger(__name__)

class OrderingService:
    """Service for managing orders, transactions, and queue matching."""

    def __init__(self, bot):
        self.bot = bot
        self.embeds = MarketplaceEmbeds()

    async def find_and_notify_matches(self, user_id: int, guild_id: int, listing_type: str, zone: str, item: str) -> bool:
        """Find matches and immediately notify the user. This is the main entry point."""
        try:
            logger.info(f"Starting match search for user {user_id}: {listing_type} {item} in {zone}")

            # Find opposite type listings
            opposite_type = "WTB" if listing_type == "WTS" else "WTS"
            current_time = datetime.now(timezone.utc)

            # Search for exact item matches first
            exact_matches = await self.bot.db_manager.execute_query(
                """
                SELECT l.*, u.username, u.reputation_avg, u.reputation_count
                FROM listings l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE l.guild_id = $1 
                  AND l.listing_type = $2 
                  AND l.zone = $3 
                  AND l.item = $4
                  AND l.expires_at > $5
                  AND l.active = TRUE
                  AND l.user_id != $6
                ORDER BY l.created_at DESC, u.reputation_avg DESC NULLS LAST
                """,
                guild_id, opposite_type, zone, item, current_time, user_id
            )

            # If no exact matches and the item isn't "All Items", look for "All Items" matches
            all_items_matches = []
            if not exact_matches and item != "All Items":
                all_items_matches = await self.bot.db_manager.execute_query(
                    """
                    SELECT l.*, u.username, u.reputation_avg, u.reputation_count
                    FROM listings l
                    LEFT JOIN users u ON l.user_id = u.user_id
                    WHERE l.guild_id = $1 
                      AND l.listing_type = $2 
                      AND l.zone = $3 
                      AND l.item = 'All Items'
                      AND l.expires_at > $4
                      AND l.active = TRUE
                      AND l.user_id != $5
                    ORDER BY l.created_at DESC, u.reputation_avg DESC NULLS LAST
                    """,
                    guild_id, opposite_type, zone, current_time, user_id
                )

            # If this is an "All Items" listing, find specific item matches
            specific_matches = []
            if item == "All Items":
                specific_matches = await self.bot.db_manager.execute_query(
                    """
                    SELECT l.*, u.username, u.reputation_avg, u.reputation_count
                    FROM listings l
                    LEFT JOIN users u ON l.user_id = u.user_id
                    WHERE l.guild_id = $1 
                      AND l.listing_type = $2 
                      AND l.zone = $3 
                      AND l.item != 'All Items'
                      AND l.expires_at > $4
                      AND l.active = TRUE
                      AND l.user_id != $5
                    ORDER BY l.created_at DESC, u.reputation_avg DESC NULLS LAST
                    """,
                    guild_id, opposite_type, zone, current_time, user_id
                )

            # Combine all matches
            all_matches = exact_matches + all_items_matches + specific_matches

            # Remove duplicates based on listing ID
            seen_ids = set()
            unique_matches = []
            for match in all_matches:
                if match['id'] not in seen_ids:
                    unique_matches.append(match)
                    seen_ids.add(match['id'])

            logger.info(f"Found {len(unique_matches)} total matches for user {user_id}")

            if unique_matches:
                # Send notification immediately
                await self.send_match_notification(user_id, unique_matches, listing_type)
                return True
            else:
                logger.info(f"No matches found for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Error in find_and_notify_matches: {e}")
            return False

    async def send_match_notification(self, user_id: int, matches: List[Dict[str, Any]], listing_type: str):
        """Send immediate match notification to user."""
        try:
            user = self.bot.get_user(user_id)
            if not user:
                logger.error(f"Could not find user {user_id} to send notification")
                return

            # Create notification embed
            embed = await self.create_match_notification_embed(matches, listing_type)

            # Create interaction view
            from bot.ui.views_ordering import MatchSelectionView
            view = MatchSelectionView(self.bot, user_id, matches, listing_type)

            # Send DM
            try:
                await user.send(embed=embed, view=view)
                logger.info(f"Successfully sent match notification to user {user_id}")
            except discord.Forbidden:
                logger.warning(f"Could not send DM to user {user_id} - DMs disabled")
            except Exception as e:
                logger.error(f"Error sending DM to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error sending match notification: {e}")

    async def create_match_notification_embed(self, matches: List[Dict[str, Any]], listing_type: str):
        """Create embed for match notifications."""
        import discord

        opposite_type = "sellers" if listing_type == "WTS" else "buyers"

        embed = discord.Embed(
            title="🎯 Matches Found!",
            description=f"Found {len(matches)} {opposite_type} for your listing!",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )

        # Show top matches
        for i, match in enumerate(matches[:5]):
            user_name = match.get('username', f"User {match['user_id']}")
            reputation = f"⭐ {match['reputation_avg']:.1f} ({match['reputation_count']} ratings)" if match.get('reputation_count', 0) > 0 else "No ratings yet"

            embed.add_field(
                name=f"{i+1}. {user_name}",
                value=(
                    f"**Item:** {match['item']}\n"
                    f"**Quantity:** {match['quantity']}\n"
                    f"**Reputation:** {reputation}\n"
                    f"**Posted:** <t:{int(match['created_at'].timestamp())}:R>"
                ),
                inline=True
            )

        if len(matches) > 5:
            embed.add_field(
                name="➕ More matches available",
                value=f"And {len(matches) - 5} more traders interested!",
                inline=False
            )

        embed.add_field(
            name="💡 Next Steps",
            value="Use the dropdown below to select a trader and create an order!",
            inline=False
        )

        embed.set_footer(text="Orders must be confirmed by both parties within 24 hours")

        return embed

    async def create_order(self, buyer_id: int, seller_id: int, listing_id: int, guild_id: int) -> Optional[int]:
        """Create a new order between two users."""
        try:
            # Get listing details
            listing = await self.bot.db_manager.execute_query(
                "SELECT * FROM listings WHERE id = $1 AND active = TRUE",
                listing_id
            )

            if not listing:
                logger.warning(f"Listing {listing_id} not found or inactive")
                return None

            listing_data = listing[0]

            # Create transaction
            transaction_id = await self.bot.db_manager.execute_query(
                """
                INSERT INTO transactions (listing_id, seller_id, buyer_id, status, created_at)
                VALUES ($1, $2, $3, 'pending', $4)
                RETURNING id
                """,
                listing_id, seller_id, buyer_id, datetime.now(timezone.utc)
            )

            if not transaction_id:
                logger.error("Failed to create transaction")
                return None

            order_id = transaction_id[0]['id']

            # Send order notifications to both parties
            await self.send_order_notifications(order_id, buyer_id, seller_id, listing_data)

            logger.info(f"Created order {order_id} between buyer {buyer_id} and seller {seller_id}")
            return order_id

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def send_order_notifications(self, order_id: int, buyer_id: int, seller_id: int, listing_data: Dict[str, Any]):
        """Send order notifications to both buyer and seller."""
        try:
            buyer = self.bot.get_user(buyer_id)
            seller = self.bot.get_user(seller_id)

            # Create notification embeds
            buyer_embed = self.create_order_notification_embed(order_id, listing_data, "buyer", seller_id)
            seller_embed = self.create_order_notification_embed(order_id, listing_data, "seller", buyer_id)

            # Create confirmation views
            from bot.ui.views_ordering import OrderConfirmationView
            buyer_view = OrderConfirmationView(self.bot, order_id, "buyer")
            seller_view = OrderConfirmationView(self.bot, order_id, "seller")

            # Send notifications
            if buyer:
                try:
                    await buyer.send(embed=buyer_embed, view=buyer_view)
                    logger.info(f"Sent order notification to buyer {buyer_id}")
                except Exception as e:
                    logger.error(f"Failed to notify buyer {buyer_id}: {e}")

            if seller:
                try:
                    await seller.send(embed=seller_embed, view=seller_view)
                    logger.info(f"Sent order notification to seller {seller_id}")
                except Exception as e:
                    logger.error(f"Failed to notify seller {seller_id}: {e}")

        except Exception as e:
            logger.error(f"Error sending order notifications: {e}")

    def create_order_notification_embed(self, order_id: int, listing_data: Dict[str, Any], user_type: str, other_user_id: int):
        """Create order notification embed."""
        import discord

        other_user = self.bot.get_user(other_user_id)
        other_username = other_user.display_name if other_user else f"User {other_user_id}"

        if user_type == "buyer":
            title = "🛒 New Order Created - You're the Buyer"
            description = f"You have a new order with **{other_username}** for their **{listing_data['listing_type']}** listing."
        else:
            title = "💰 New Order Created - You're the Seller"
            description = f"**{other_username}** wants to order from your **{listing_data['listing_type']}** listing."

        embed = discord.Embed(
            title=title,
            description=description,
            color=0x3498db,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📦 Order Details",
            value=(
                f"**Order ID:** #{order_id}\n"
                f"**Item:** {listing_data['item']}\n"
                f"**Quantity:** {listing_data['quantity']}\n"
                f"**Zone:** {listing_data['zone'].title()}"
            ),
            inline=True
        )

        if listing_data.get('notes'):
            embed.add_field(
                name="📝 Notes",
                value=listing_data['notes'][:200] + ("..." if len(listing_data['notes']) > 200 else ""),
                inline=False
            )

        embed.add_field(
            name="⚡ Next Steps",
            value=(
                "Both parties need to confirm this order.\n"
                "Use the buttons below to confirm or cancel."
            ),
            inline=False
        )

        embed.set_footer(text="Orders expire after 24 hours if not confirmed by both parties")

        return embed

    async def confirm_order(self, order_id: int, user_id: int, user_type: str) -> bool:
        """Confirm an order from buyer or seller side."""
        try:
            # Get transaction details
            transaction = await self.bot.db_manager.execute_query(
                "SELECT * FROM transactions WHERE id = $1 AND status = 'pending'",
                order_id
            )

            if not transaction:
                logger.warning(f"Transaction {order_id} not found")
                return False

            transaction_data = transaction[0]

            # Verify user is part of this transaction
            if user_type == "buyer" and transaction_data['buyer_id'] != user_id:
                logger.warning(f"User {user_id} is not the buyer for order {order_id}")
                return False
            elif user_type == "seller" and transaction_data['seller_id'] != user_id:
                logger.warning(f"User {user_id} is not the seller for order {order_id}")
                return False

            # Update confirmation status
            if user_type == "buyer":
                await self.bot.db_manager.execute_command(
                    "UPDATE transactions SET buyer_confirmed = TRUE WHERE id = $1",
                    order_id
                )
            else:
                await self.bot.db_manager.execute_command(
                    "UPDATE transactions SET seller_confirmed = TRUE WHERE id = $1",
                    order_id
                )

            # Check if both parties confirmed
            updated_transaction = await self.bot.db_manager.execute_query(
                "SELECT * FROM transactions WHERE id = $1",
                order_id
            )

            if updated_transaction:
                trans_data = updated_transaction[0]
                if trans_data.get('buyer_confirmed') and trans_data.get('seller_confirmed'):
                    # Both confirmed - move to confirmed status
                    await self.bot.db_manager.execute_command(
                        "UPDATE transactions SET status = 'confirmed' WHERE id = $1",
                        order_id
                    )

                    # Send confirmation notifications
                    await self.send_both_confirmed_notification(order_id, trans_data)

                    logger.info(f"Order {order_id} confirmed by both parties")

            return True

        except Exception as e:
            logger.error(f"Error confirming order: {e}")
            return False

    async def send_both_confirmed_notification(self, order_id: int, transaction_data: Dict[str, Any]):
        """Send notification when both parties have confirmed."""
        try:
            buyer = self.bot.get_user(transaction_data['buyer_id'])
            seller = self.bot.get_user(transaction_data['seller_id'])

            # Get listing details
            listing = await self.bot.db_manager.execute_query(
                "SELECT * FROM listings WHERE id = $1",
                transaction_data['listing_id']
            )

            if not listing:
                return

            listing_data = listing[0]

            # Create confirmed embed
            embed = self.create_confirmed_embed(order_id, listing_data, transaction_data)

            # Create completion views
            from bot.ui.views_ordering import OrderCompletionView
            buyer_view = OrderCompletionView(self.bot, order_id, "buyer")
            seller_view = OrderCompletionView(self.bot, order_id, "seller")

            # Send to both parties
            if buyer:
                try:
                    await buyer.send(embed=embed, view=buyer_view)
                    logger.info(f"Sent confirmation to buyer {transaction_data['buyer_id']}")
                except Exception as e:
                    logger.error(f"Failed to notify buyer: {e}")

            if seller:
                try:
                    await seller.send(embed=embed, view=seller_view)
                    logger.info(f"Sent confirmation to seller {transaction_data['seller_id']}")
                except Exception as e:
                    logger.error(f"Failed to notify seller: {e}")

        except Exception as e:
            logger.error(f"Error sending both confirmed notification: {e}")

    def create_confirmed_embed(self, order_id: int, listing_data: Dict[str, Any], transaction_data: Dict[str, Any]):
        """Create embed for confirmed orders."""
        import discord

        embed = discord.Embed(
            title="✅ Order Confirmed!",
            description="Both parties have confirmed this order. You can now proceed with the trade.",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )

        buyer = self.bot.get_user(transaction_data['buyer_id'])
        seller = self.bot.get_user(transaction_data['seller_id'])

        embed.add_field(
            name="👥 Trade Participants",
            value=(
                f"**Buyer:** {buyer.display_name if buyer else 'Unknown'}\n"
                f"**Seller:** {seller.display_name if seller else 'Unknown'}"
            ),
            inline=True
        )

        embed.add_field(
            name="📦 Order Details",
            value=(
                f"**Order ID:** #{order_id}\n"
                f"**Item:** {listing_data['item']}\n"
                f"**Quantity:** {listing_data['quantity']}\n"
                f"**Zone:** {listing_data['zone'].title()}"
            ),
            inline=True
        )

        embed.add_field(
            name="🎯 Next Steps",
            value=(
                "1. Meet in-game to complete the trade\n"
                "2. Complete the order using the button below\n"
                "3. Rate each other after successful trade"
            ),
            inline=False
        )

        embed.set_footer(text="Use the 'Complete Order' button when trade is finished")

        return embed

    async def complete_order(self, order_id: int, user_id: int, user_type: str) -> bool:
        """Mark order as completed and send rating requests."""
        try:
            # Get transaction
            transaction = await self.bot.db_manager.execute_query(
                "SELECT * FROM transactions WHERE id = $1 AND status = 'confirmed'",
                order_id
            )

            if not transaction:
                logger.warning(f"Transaction {order_id} not found or not confirmed")
                return False

            transaction_data = transaction[0]

            # Verify user is part of this transaction
            if user_type == "buyer" and transaction_data['buyer_id'] != user_id:
                return False
            elif user_type == "seller" and transaction_data['seller_id'] != user_id:
                return False

            # Mark as completed
            await self.bot.db_manager.execute_command(
                """
                UPDATE transactions 
                SET status = 'completed', completed_at = $1 
                WHERE id = $2
                """,
                datetime.now(timezone.utc), order_id
            )

            # Mark listing as inactive
            await self.bot.db_manager.execute_command(
                "UPDATE listings SET active = FALSE WHERE id = $1",
                transaction_data['listing_id']
            )

            # Send rating requests immediately
            await self.send_rating_requests(order_id, transaction_data)

            # Refresh marketplace embeds
            listing = await self.bot.db_manager.execute_query(
                "SELECT guild_id, listing_type, zone FROM listings WHERE id = $1",
                transaction_data['listing_id']
            )

            if listing:
                listing_data = listing[0]
                from bot.services.marketplace import MarketplaceService
                marketplace_service = MarketplaceService(self.bot)
                await marketplace_service.refresh_marketplace_embeds_for_zone(
                    listing_data['guild_id'], 
                    listing_data['listing_type'], 
                    listing_data['zone']
                )

            logger.info(f"Order {order_id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error completing order: {e}")
            return False

    async def send_rating_requests(self, order_id: int, transaction_data: Dict[str, Any]):
        """Send rating requests to both parties immediately."""
        try:
            buyer = self.bot.get_user(transaction_data['buyer_id'])
            seller = self.bot.get_user(transaction_data['seller_id'])

            # Create rating embeds
            buyer_embed = self.create_rating_request_embed(order_id, "seller", transaction_data['seller_id'])
            seller_embed = self.create_rating_request_embed(order_id, "buyer", transaction_data['buyer_id'])

            # Create rating views
            from bot.ui.views_ordering import RatingView
            buyer_view = RatingView(self.bot, order_id, transaction_data['seller_id'])
            seller_view = RatingView(self.bot, order_id, transaction_data['buyer_id'])

            # Send rating requests
            if buyer:
                try:
                    await buyer.send(embed=buyer_embed, view=buyer_view)
                    logger.info(f"Sent rating request to buyer {transaction_data['buyer_id']}")
                except Exception as e:
                    logger.error(f"Failed to send rating request to buyer: {e}")

            if seller:
                try:
                    await seller.send(embed=seller_embed, view=seller_view)
                    logger.info(f"Sent rating request to seller {transaction_data['seller_id']}")
                except Exception as e:
                    logger.error(f"Failed to send rating request to seller: {e}")

        except Exception as e:
            logger.error(f"Error sending rating requests: {e}")

    def create_rating_request_embed(self, order_id: int, target_type: str, target_user_id: int):
        """Create rating request embed."""
        import discord

        target_user = self.bot.get_user(target_user_id)
        target_name = target_user.display_name if target_user else f"User {target_user_id}"

        embed = discord.Embed(
            title="⭐ Rate Your Trading Partner",
            description=f"Please rate your experience trading with **{target_name}**.",
            color=0xffd700,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="📊 Rating Scale",
            value=(
                "⭐ **1 Star** - Poor experience\n"
                "⭐⭐ **2 Stars** - Below average\n"
                "⭐⭐⭐ **3 Stars** - Average\n"
                "⭐⭐⭐⭐ **4 Stars** - Good\n"
                "⭐⭐⭐⭐⭐ **5 Stars** - Excellent"
            ),
            inline=False
        )

        embed.add_field(
            name="💭 Optional Comment",
            value="You can add a comment to help other traders know about your experience.",
            inline=False
        )

        embed.set_footer(text=f"Order #{order_id} • Rating helps build trust in the community")

        return embed

    async def cancel_order(self, order_id: int, user_id: int, reason: str = "") -> bool:
        """Cancel an order."""
        try:
            # Get transaction
            transaction = await self.bot.db_manager.execute_query(
                "SELECT * FROM transactions WHERE id = $1 AND status IN ('pending', 'confirmed')",
                order_id
            )

            if not transaction:
                return False

            transaction_data = transaction[0]

            # Verify user is part of this transaction
            if user_id not in [transaction_data['buyer_id'], transaction_data['seller_id']]:
                return False

            # Cancel transaction
            await self.bot.db_manager.execute_command(
                "UPDATE transactions SET status = 'cancelled' WHERE id = $1",
                order_id
            )

            logger.info(f"Order {order_id} cancelled by user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def get_user_order_history(self, user_id: int, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's order history."""
        try:
            orders = await self.bot.db_manager.execute_query(
                """
                SELECT t.*, l.item, l.zone, l.listing_type,
                       CASE 
                         WHEN t.buyer_id = $1 THEN u_seller.username
                         ELSE u_buyer.username
                       END as other_party_name
                FROM transactions t
                JOIN listings l ON t.listing_id = l.id
                LEFT JOIN users u_seller ON t.seller_id = u_seller.user_id
                LEFT JOIN users u_buyer ON t.buyer_id = u_buyer.user_id
                WHERE (t.buyer_id = $1 OR t.seller_id = $1)
                  AND l.guild_id = $2
                ORDER BY t.created_at DESC
                LIMIT $3
                """,
                user_id, guild_id, limit
            )
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting user order history: {e}")
            return []