from django.core.management.base import BaseCommand
import asyncio
import logging
from auto_validator.discord_bot.bot import DiscordBot

class Command(BaseCommand):
    help = 'Run the Discord bot'

    def handle(self, *args, **kwargs):
        logger = logging.getLogger('bot')
        bot = DiscordBot(logger)

        asyncio.run(bot.start_bot())