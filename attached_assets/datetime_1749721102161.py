class DateTimeSelectView(discord.ui.View):
    """View for selecting date and time."""

    def __init__(self, bot, listing_data: Dict[str, Any]):
        super().__init__(timeout=300)
        self.bot = bot
        self.listing_data = listing_data

        # Add date options (today + 14 days)
        from datetime import datetime, timedelta

        date_options = []
        for i in range(15):  # 0-14 days ahead
            date = datetime.now() + timedelta(days=i)
            label = date.strftime("%A, %B %d")
            if i == 0:
                label += " (Today)"
            elif i == 1:
                label += " (Tomorrow)"

            date_options.append(
                discord.SelectOption(
                    label=label,
                    value=date.strftime("%Y-%m-%d")
                )
            )

        self.date_select.options = date_options[:25]  # Discord limit

        # Add time options (00:00 to 23:00)
        time_options = []
        for hour in range(24):
            time_str = f"{hour:02d}:00"
            time_options.append(
                discord.SelectOption(label=time_str, value=time_str)
            )

        self.time_select.options = time_options

    @discord.ui.select(placeholder="Choose a date...")
    async def date_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle date selection."""
        self.listing_data['date'] = select.values[0]
        await interaction.response.send_message(
            f"✅ Date selected: {select.values[0]}\nNow choose a time...",
            ephemeral=True
        )

    @discord.ui.select(placeholder="Choose a time...")
    async def time_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle time selection."""
        self.listing_data['time'] = select.values[0]

        # If both date and time are selected, create the listing
        if 'date' in self.listing_data and 'time' in self.listing_data:
            await interaction.response.defer()
            await self.create_listing(interaction)
        else:
            await interaction.response.send_message(
                f"✅ Time selected: {select.values[0]}\nPlease select a date first.",
                ephemeral=True
            )

    @discord.ui.button(label="Custom Time", style=discord.ButtonStyle.secondary)
    async def custom_time_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle custom time input."""
        modal = CustomTimeModal(self.bot, self.listing_data)
        await interaction.response.send_modal(modal)