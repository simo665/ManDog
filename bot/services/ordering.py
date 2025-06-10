"""
Redesigned ordering system with confirmation workflow and admin moderation.
"""

import logging
import discord
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

class OrderingService:
    """Redesigned ordering service with confirmation and rating workflow."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_confirmations = {}  # Track pending order confirmations
        self.pending_ratings = {}  # Track pending ratings

    async def find_and_notify_matches(self, user_id: int, guild_id: int, listing_type: str, zone: str, item: str) -> bool:
        """Find matching listings and initiate order confirmation process."""
        try:
            # Determine opposite listing type
            opposite_type = "WTS" if listing_type == "WTB" else "WTB"

            logger.info(f"🔍 MATCHING DEBUG: Starting match search for user {user_id}")
            logger.info(f"🔍 MATCHING DEBUG: Looking for {opposite_type} listings in {zone} zone for item '{item}'")
            logger.info(f"🔍 MATCHING DEBUG: Original listing type: {listing_type}, Opposite type: {opposite_type}")

            # First, let's see ALL listings in this zone to debug
            all_zone_listings = await self.bot.db_manager.execute_query(
                """
                SELECT id, user_id, item, listing_type, zone, active, created_at
                FROM listings 
                WHERE guild_id = $1 AND zone = $2 AND active = TRUE
                ORDER BY created_at DESC
                """,
                guild_id, zone
            )

            logger.info(f"🔍 MATCHING DEBUG: Found {len(all_zone_listings)} total active listings in {zone} zone:")
            for listing in all_zone_listings:
                logger.info(f"  - ID: {listing['id']}, User: {listing['user_id']}, Type: {listing['listing_type']}, Item: '{listing['item']}'")

            # Find matching listings
            matches = await self.bot.db_manager.execute_query(
                """
                SELECT id, user_id, item, quantity, notes, subcategory, scheduled_time
                FROM listings 
                WHERE guild_id = $1 AND listing_type = $2 AND zone = $3 
                AND LOWER(item) = LOWER($4) AND active = TRUE AND user_id != $5
                ORDER BY created_at ASC
                """,
                guild_id, opposite_type, zone, item, user_id
            )

            logger.info(f"🔍 MATCHING DEBUG: Query parameters:")
            logger.info(f"  - guild_id: {guild_id}")
            logger.info(f"  - opposite_type: {opposite_type}")
            logger.info(f"  - zone: {zone}")
            logger.info(f"  - item (lowercase): '{item.lower()}'")
            logger.info(f"  - user_id (excluded): {user_id}")

            logger.info(f"🔍 MATCHING DEBUG: Found {len(matches)} potential matches")

            if not matches:
                logger.warning(f"❌ MATCHING DEBUG: No matches found for {listing_type} '{item}' in {zone}")
                
                # Let's check why - look for opposite type listings with similar items
                similar_items = await self.bot.db_manager.execute_query(
                    """
                    SELECT id, user_id, item, listing_type
                    FROM listings 
                    WHERE guild_id = $1 AND listing_type = $2 AND zone = $3 AND active = TRUE
                    ORDER BY created_at ASC
                    """,
                    guild_id, opposite_type, zone
                )
                
                logger.info(f"🔍 MATCHING DEBUG: Available {opposite_type} listings in {zone}:")
                for similar in similar_items:
                    item_match = similar['item'].lower() == item.lower()
                    user_match = similar['user_id'] != user_id
                    logger.info(f"  - ID: {similar['id']}, User: {similar['user_id']}, Item: '{similar['item']}' | Item Match: {item_match}, User Different: {user_match}")
                
                return False

            # Get guild and users
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return False

            requester = guild.get_member(user_id)
            if not requester:
                logger.error(f"User {user_id} not found in guild {guild_id}")
                return False

            # Process each match (limit to 1 to prevent spam)
            matches_found = False
            for i, match in enumerate(matches[:1]):  # Only process first match to prevent spam
                matcher_id = match['user_id']
                logger.info(f"🤝 MATCHING DEBUG: Processing match {i+1}/{len(matches)} - Matcher ID: {matcher_id}")
                
                matcher = guild.get_member(matcher_id)

                if not matcher:
                    logger.warning(f"❌ MATCHING DEBUG: Matcher {matcher_id} not found in guild {guild.name}")
                    continue

                logger.info(f"✅ MATCHING DEBUG: Found matcher: {matcher.display_name} ({matcher.id})")
                logger.info(f"🤝 MATCHING DEBUG: Initiating order confirmation between {requester.display_name} and {matcher.display_name}")

                # Initiate order confirmation
                try:
                    await self.initiate_order_confirmation(
                        guild, requester, matcher, match, listing_type, zone, item
                    )
                    logger.info(f"✅ MATCHING DEBUG: Successfully initiated order confirmation for match {i+1}")
                    matches_found = True
                except Exception as init_error:
                    logger.error(f"❌ MATCHING DEBUG: Failed to initiate order confirmation: {init_error}")

            logger.info(f"🔍 MATCHING DEBUG: Final result - Matches found: {matches_found}")
            return matches_found

        except Exception as e:
            logger.error(f"Error finding matches: {e}")
            return False

    async def initiate_order_confirmation(self, guild: discord.Guild, requester: discord.Member, 
                                        matcher: discord.Member, match_data: Dict[str, Any], 
                                        requester_type: str, zone: str, item: str):
        """Send order confirmation DMs to both parties."""
        try:
            logger.info(f"📨 ORDER DEBUG: Starting order confirmation initiation")
            logger.info(f"📨 ORDER DEBUG: Guild: {guild.name}, Requester: {requester.display_name}, Matcher: {matcher.display_name}")
            logger.info(f"📨 ORDER DEBUG: Requester type: {requester_type}, Zone: {zone}, Item: '{item}'")
            
            # Create unique order ID with microseconds to prevent duplicates
            timestamp = datetime.now().timestamp()
            order_id = f"{guild.id}_{requester.id}_{matcher.id}_{int(timestamp * 1000000)}"
            logger.info(f"📨 ORDER DEBUG: Generated order ID: {order_id}")

            # Determine buyer and seller
            if requester_type == "WTB":
                buyer = requester
                seller = matcher
                buyer_type = "WTB"
                seller_type = "WTS"
            else:
                buyer = matcher
                seller = requester
                buyer_type = "WTS"
                seller_type = "WTB"

            logger.info(f"📨 ORDER DEBUG: Buyer: {buyer.display_name} ({buyer_type}), Seller: {seller.display_name} ({seller_type})")

            # Store order confirmation data
            self.pending_confirmations[order_id] = {
                'guild_id': guild.id,
                'buyer_id': buyer.id,
                'seller_id': seller.id,
                'item': item,
                'zone': zone,
                'quantity': match_data.get('quantity', 1),
                'notes': match_data.get('notes', ''),
                'listing_id': match_data['id'],
                'confirmations': set(),
                'created_at': datetime.now(timezone.utc)
            }

            # Create confirmation embeds and views
            from bot.ui.views_ordering import OrderConfirmationView

            # Send to buyer
            buyer_embed = self.create_order_confirmation_embed(
                "buyer", seller, item, zone, match_data
            )
            buyer_view = OrderConfirmationView(self.bot, order_id, "buyer")

            try:
                logger.info(f"📨 ORDER DEBUG: Attempting to send DM to buyer {buyer.display_name}")
                await buyer.send(embed=buyer_embed, view=buyer_view)
                logger.info(f"✅ ORDER DEBUG: Successfully sent order confirmation to buyer {buyer.display_name}")
            except discord.Forbidden:
                logger.warning(f"❌ ORDER DEBUG: Cannot DM buyer {buyer.display_name} - DMs disabled")
            except Exception as buyer_dm_error:
                logger.error(f"❌ ORDER DEBUG: Failed to send DM to buyer {buyer.display_name}: {buyer_dm_error}")

            # Send to seller
            seller_embed = self.create_order_confirmation_embed(
                "seller", buyer, item, zone, match_data
            )
            seller_view = OrderConfirmationView(self.bot, order_id, "seller")

            try:
                logger.info(f"📨 ORDER DEBUG: Attempting to send DM to seller {seller.display_name}")
                await seller.send(embed=seller_embed, view=seller_view)
                logger.info(f"✅ ORDER DEBUG: Successfully sent order confirmation to seller {seller.display_name}")
            except discord.Forbidden:
                logger.warning(f"❌ ORDER DEBUG: Cannot DM seller {seller.display_name} - DMs disabled")
            except Exception as seller_dm_error:
                logger.error(f"❌ ORDER DEBUG: Failed to send DM to seller {seller.display_name}: {seller_dm_error}")

            logger.info(f"📨 ORDER DEBUG: Order confirmation process completed for order {order_id}")

        except Exception as e:
            logger.error(f"Error initiating order confirmation: {e}")

    def create_order_confirmation_embed(self, role: str, other_party: discord.Member, 
                                      item: str, zone: str, match_data: Dict[str, Any]) -> discord.Embed:
        """Create order confirmation embed."""
        embed = discord.Embed(
            title="🤝 Trade Match Found!",
            description=f"A potential trade has been found for **{item}** in {zone.title()}",
            color=0x00FF00,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="🎯 Item",
            value=item,
            inline=True
        )

        embed.add_field(
            name="📍 Zone",
            value=zone.title(),
            inline=True
        )

        embed.add_field(
            name="📦 Quantity",
            value=str(match_data.get('quantity', 1)),
            inline=True
        )

        if role == "buyer":
            embed.add_field(
                name="💰 Seller",
                value=other_party.mention,
                inline=False
            )
        else:
            embed.add_field(
                name="🛒 Buyer",
                value=other_party.mention,
                inline=False
            )

        if match_data.get('notes'):
            embed.add_field(
                name="📝 Notes",
                value=match_data['notes'][:500],
                inline=False
            )

        embed.add_field(
            name="⏰ Next Steps",
            value="Click **Confirm Trade** if you want to proceed with this transaction.",
            inline=False
        )

        embed.set_footer(text="Both parties must confirm to proceed")
        return embed

    async def handle_order_confirmation(self, order_id: str, user_id: int, confirmed: bool):
        """Handle order confirmation response."""
        try:
            logger.info(f"🔄 CONFIRMATION DEBUG: Handling confirmation for order {order_id} by user {user_id}")
            logger.info(f"🔄 CONFIRMATION DEBUG: Confirmed: {confirmed}")
            logger.info(f"🔄 CONFIRMATION DEBUG: Pending orders: {list(self.pending_confirmations.keys())}")
            
            if order_id not in self.pending_confirmations:
                logger.warning(f"❌ CONFIRMATION DEBUG: Order {order_id} not found in pending confirmations")
                logger.warning(f"❌ CONFIRMATION DEBUG: Available orders: {list(self.pending_confirmations.keys())}")
                return False

            order_data = self.pending_confirmations[order_id]
            logger.info(f"🔄 CONFIRMATION DEBUG: Found order data for {order_id}")

            # Verify user is part of this order
            if user_id not in [order_data['buyer_id'], order_data['seller_id']]:
                logger.warning(f"❌ CONFIRMATION DEBUG: User {user_id} not part of order {order_id}")
                return False

            if confirmed:
                order_data['confirmations'].add(user_id)
                logger.info(f"✅ CONFIRMATION DEBUG: User {user_id} confirmed order {order_id}")
                logger.info(f"🔄 CONFIRMATION DEBUG: Current confirmations: {order_data['confirmations']}")

                # Check if both parties confirmed
                buyer_confirmed = order_data['buyer_id'] in order_data['confirmations']
                seller_confirmed = order_data['seller_id'] in order_data['confirmations']
                
                logger.info(f"🔄 CONFIRMATION DEBUG: Buyer confirmed: {buyer_confirmed}, Seller confirmed: {seller_confirmed}")

                if buyer_confirmed and seller_confirmed:
                    logger.info(f"🎉 CONFIRMATION DEBUG: Both parties confirmed! Completing order {order_id}")
                    # Both confirmed - proceed to trade completion
                    await self.complete_order(order_id)
                    return True
                else:
                    logger.info(f"⏳ CONFIRMATION DEBUG: Waiting for other party to confirm")
                    return True
            else:
                # Order declined - notify other party
                user_role = "buyer" if user_id == order_data['buyer_id'] else "seller"
                logger.info(f"❌ CONFIRMATION DEBUG: User {user_id} ({user_role}) declined order {order_id}")
                await self.cancel_order(order_id, f"declined by {user_role}")
                return True  # Return True because the decline was processed successfully

        except Exception as e:
            logger.error(f"Error handling order confirmation: {e}")
            return False

    async def complete_order(self, order_id: str):
        """Complete the order and send rating requests."""
        try:
            order_data = self.pending_confirmations.pop(order_id, None)
            if not order_data:
                return

            # Get guild and members
            guild = self.bot.get_guild(order_data['guild_id'])
            if not guild:
                return

            buyer = guild.get_member(order_data['buyer_id'])
            seller = guild.get_member(order_data['seller_id'])

            if not buyer or not seller:
                logger.error(f"Could not find buyer or seller for order {order_id}")
                return

            # Remove the matched listing
            await self.bot.db_manager.remove_listing(order_data['listing_id'], seller.id)

            # Create transaction record
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO transactions (buyer_id, seller_id, item, zone, quantity, status, created_at)
                VALUES ($1, $2, $3, $4, $5, 'completed', $6)
                """,
                buyer.id, seller.id, order_data['item'], order_data['zone'], 
                order_data['quantity'], datetime.now(timezone.utc)
            )

            # Send completion messages
            completion_embed = discord.Embed(
                title="🎉 Trade Confirmed!",
                description="**Both parties have confirmed the trade!**\n\nPlease trade the item and rate each other below.",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc)
            )

            completion_embed.add_field(
                name="🎯 Item",
                value=order_data['item'],
                inline=True
            )

            completion_embed.add_field(
                name="📍 Zone", 
                value=order_data['zone'].title(),
                inline=True
            )

            completion_embed.add_field(
                name="📦 Quantity",
                value=str(order_data['quantity']),
                inline=True
            )

            completion_embed.add_field(
                name="📝 Next Steps",
                value="1. Complete the item trade in-game\n2. Rate your trade partner below",
                inline=False
            )

            # Send to both parties with rating buttons
            from bot.ui.views_ordering import OrderCompletionView

            # Send to buyer
            buyer_completion_embed = completion_embed.copy()
            buyer_completion_embed.add_field(
                name="💰 Your Trade Partner (Seller)",
                value=f"{seller.mention}\n*Please complete the trade and rate them*",
                inline=False
            )
            buyer_view = OrderCompletionView(self.bot, order_id, "buyer", seller.id)

            try:
                await buyer.send(embed=buyer_completion_embed, view=buyer_view)
                logger.info(f"✅ Sent trade completion message to buyer {buyer.display_name}")
            except discord.Forbidden:
                logger.warning(f"❌ Cannot send DM to buyer {buyer.display_name}")

            # Send to seller
            seller_completion_embed = completion_embed.copy()
            seller_completion_embed.add_field(
                name="🛒 Your Trade Partner (Buyer)",
                value=f"{buyer.mention}\n*Please complete the trade and rate them*",
                inline=False
            )
            seller_view = OrderCompletionView(self.bot, order_id, "seller", buyer.id)

            try:
                await seller.send(embed=seller_completion_embed, view=seller_view)
                logger.info(f"✅ Sent trade completion message to seller {seller.display_name}")
            except discord.Forbidden:
                logger.warning(f"❌ Cannot send DM to seller {seller.display_name}")

            # Store for rating tracking
            self.pending_ratings[order_id] = {
                'buyer_id': buyer.id,
                'seller_id': seller.id,
                'guild_id': guild.id,
                'item': order_data['item'],
                'zone': order_data['zone'],
                'ratings': {}
            }

            logger.info(f"🎉 Order {order_id} completed successfully, rating phase initiated")

        except Exception as e:
            logger.error(f"Error completing order: {e}")

    async def cancel_order(self, order_id: str, reason: str):
        """Cancel an order and notify both parties."""
        try:
            order_data = self.pending_confirmations.pop(order_id, None)
            if not order_data:
                logger.warning(f"Order {order_id} not found for cancellation")
                return

            guild = self.bot.get_guild(order_data['guild_id'])
            if not guild:
                return

            buyer = guild.get_member(order_data['buyer_id'])
            seller = guild.get_member(order_data['seller_id'])

            cancel_embed = discord.Embed(
                title="❌ Trade Cancelled",
                description=f"The trade for **{order_data['item']}** has been cancelled ({reason}).",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )

            cancel_embed.add_field(
                name="🎯 Item",
                value=order_data['item'],
                inline=True
            )

            cancel_embed.add_field(
                name="📍 Zone",
                value=order_data['zone'].title(),
                inline=True
            )

            # Notify both parties and update their messages
            from bot.ui.views_ordering import OrderConfirmationView
            
            for member in [buyer, seller]:
                if member:
                    try:
                        # Send cancellation message
                        await member.send(embed=cancel_embed)
                        logger.info(f"Sent cancellation notification to {member.display_name}")
                    except discord.Forbidden:
                        logger.warning(f"Cannot send DM to {member.display_name}")
                    except Exception as dm_error:
                        logger.error(f"Error sending cancellation DM to {member.display_name}: {dm_error}")

            logger.info(f"Order {order_id} cancelled: {reason}")

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")

    async def handle_rating_submission(self, order_id: str, rater_id: int, rated_id: int, rating: int, comment: str = ""):
        """Handle rating submission with admin moderation for low ratings."""
        try:
            if order_id not in self.pending_ratings:
                logger.warning(f"Rating order {order_id} not found")
                return False

            rating_data = self.pending_ratings[order_id]

            # Store the rating
            rating_data['ratings'][rater_id] = {
                'rated_id': rated_id,
                'rating': rating,
                'comment': comment,
                'timestamp': datetime.now(timezone.utc)
            }

            # Check if rating needs admin approval (rating < 3)
            if rating < 3:
                await self.create_admin_moderation_ticket(order_id, rater_id, rated_id, rating, comment)
                return True

            # Good rating - process immediately
            await self.process_rating(rater_id, rated_id, rating, comment, rating_data['guild_id'])

            # Check if both ratings are complete
            if len(rating_data['ratings']) == 2:
                # Both ratings submitted, clean up
                self.pending_ratings.pop(order_id, None)
                logger.info(f"All ratings completed for order {order_id}")

            return True

        except Exception as e:
            logger.error(f"Error handling rating submission: {e}")
            return False

    async def create_admin_moderation_ticket(self, order_id: str, rater_id: int, rated_id: int, rating: int, comment: str):
        """Create admin moderation ticket for low ratings."""
        try:
            rating_data = self.pending_ratings[order_id]
            guild = self.bot.get_guild(rating_data['guild_id'])
            if not guild:
                return

            # Find or create moderation category
            moderation_category = None
            for category in guild.categories:
                if category.name.lower() == "moderation tickets":
                    moderation_category = category
                    break

            if not moderation_category:
                moderation_category = await guild.create_category(
                    "Moderation Tickets",
                    reason="Created for rating moderation"
                )

            # Create private channel
            rater = guild.get_member(rater_id)
            rated = guild.get_member(rated_id)

            channel_name = f"rating-{rater.display_name}-{rated.display_name}"[:50]

            # Create channel with restricted permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                rater: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                rated: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }

            # Add admin roles
            admin_roles = await self.get_admin_roles(guild)
            for role in admin_roles:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            ticket_channel = await guild.create_text_channel(
                channel_name,
                category=moderation_category,
                overwrites=overwrites,
                reason=f"Rating moderation for order {order_id}"
            )

            # Send moderation embed
            from bot.ui.views_ordering import RatingModerationView

            moderation_embed = discord.Embed(
                title="⚠️ Rating Requires Moderation",
                description="A low rating has been submitted and requires admin approval.",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )

            moderation_embed.add_field(name="🎯 Item", value=rating_data['item'], inline=True)
            moderation_embed.add_field(name="📍 Zone", value=rating_data['zone'], inline=True)
            moderation_embed.add_field(name="⭐ Rating", value=f"{rating}/5", inline=True)
            moderation_embed.add_field(name="👤 Rater", value=rater.mention, inline=True)
            moderation_embed.add_field(name="👥 Rated User", value=rated.mention, inline=True)
            moderation_embed.add_field(name="📝 Comment", value=comment or "No comment provided", inline=False)

            view = RatingModerationView(self.bot, order_id, rater_id, rated_id, rating, comment)

            await ticket_channel.send(
                content=f"@here New rating moderation required",
                embed=moderation_embed,
                view=view
            )

            logger.info(f"Created moderation ticket {ticket_channel.name} for order {order_id}")

        except Exception as e:
            logger.error(f"Error creating admin moderation ticket: {e}")

    async def get_admin_roles(self, guild: discord.Guild) -> List[discord.Role]:
        """Get admin roles for the guild."""
        admin_roles = []
        admin_role_names = ["admin", "administrator", "mandok admin", "marketplace admin", "mod", "moderator"]

        for role in guild.roles:
            if (role.permissions.administrator or 
                role.name.lower() in admin_role_names):
                admin_roles.append(role)

        return admin_roles

    async def handle_admin_rating_decision(self, order_id: str, rater_id: int, rated_id: int, 
                                         rating: int, comment: str, approved: bool, admin_id: int):
        """Handle admin decision on rating moderation."""
        try:
            if approved:
                # Process the rating
                rating_data = self.pending_ratings.get(order_id)
                if rating_data:
                    await self.process_rating(rater_id, rated_id, rating, comment, rating_data['guild_id'])
                    logger.info(f"Admin {admin_id} approved rating for order {order_id}")

                    # Check if both ratings are complete
                    if len(rating_data['ratings']) == 2:
                        self.pending_ratings.pop(order_id, None)
            else:
                # Remove the rating from pending
                if order_id in self.pending_ratings:
                    rating_data = self.pending_ratings[order_id]
                    rating_data['ratings'].pop(rater_id, None)
                    logger.info(f"Admin {admin_id} rejected rating for order {order_id}")

            return True

        except Exception as e:
            logger.error(f"Error handling admin rating decision: {e}")
            return False

    async def process_rating(self, rater_id: int, rated_id: int, rating: int, comment: str, guild_id: int):
        """Process and store a rating in the database."""
        try:
            # Store rating in database
            await self.bot.db_manager.execute_command(
                """
                INSERT INTO ratings (rater_id, rated_id, guild_id, rating, comment, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                rater_id, rated_id, guild_id, rating, comment, datetime.now(timezone.utc)
            )

            # Update user reputation
            await self.update_user_reputation(rated_id)

            logger.info(f"Processed rating: {rater_id} rated {rated_id} with {rating}/5")

        except Exception as e:
            logger.error(f"Error processing rating: {e}")

    async def update_user_reputation(self, user_id: int):
        """Update user reputation based on ratings."""
        try:
            # Calculate new reputation
            reputation_data = await self.bot.db_manager.execute_query(
                """
                SELECT 
                    COUNT(*) as total_ratings,
                    AVG(rating) as average_rating,
                    SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_ratings
                FROM ratings 
                WHERE rated_id = $1
                """,
                user_id
            )

            if reputation_data:
                data = reputation_data[0]
                avg_rating = float(data['average_rating']) if data['average_rating'] else 0
                total_ratings = data['total_ratings']
                positive_ratings = data['positive_ratings']

                # Update user reputation
                await self.bot.db_manager.execute_command(
                    """
                    INSERT INTO users (user_id, average_rating, total_ratings, positive_ratings, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        average_rating = $2,
                        total_ratings = $3,
                        positive_ratings = $4,
                        updated_at = $5
                    """,
                    user_id, avg_rating, total_ratings, positive_ratings, datetime.now(timezone.utc)
                )

                logger.info(f"Updated reputation for user {user_id}: {avg_rating:.2f}/5 ({total_ratings} ratings)")

        except Exception as e:
            logger.error(f"Error updating user reputation: {e}")