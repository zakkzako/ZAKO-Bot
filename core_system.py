async def handle_reaction_event(self, reaction, user):
    try:
        channel = await self.bot.fetch_channel(reaction.channel_id)
        if channel is None:
            logging.error('Channel not found: channel_id=%s', reaction.channel_id)
            return
        # Proceed with handling the reaction event...
    except discord.NotFound as e:
        logging.error('Discord NotFound error while fetching channel: %s', e)
    except Exception as e:
        logging.error('Unexpected error in handle_reaction_event: %s', e)