"""
This module defines a Discord bot with commands and utilities for sending messages,
managing invites, and setting permissions in Discord channels.

Classes:
- DiscordBot: A custom Discord bot that extends `commands.Bot` to include additional functionality
such as sending messages, creating invite links, and managing channel permissions.

Usage:
Instantiate `DiscordBot` with a configuration and call `start_bot()` to run the bot.
"""

import asyncio
import json
import logging
import re
from typing import Any

import discord
import redis
from discord.ext import commands
from django.conf import settings

from .bot_utils import validate_bot_settings
from .subnet_config import ChannelName, SubnetConfigManager, UserID


class DiscordBot(commands.Bot):
    def __init__(self, logger: logging.Logger | None = None) -> None:
        validate_bot_settings()
        self.config: dict[str, Any] = {
            "DISCORD_BOT_TOKEN": settings.DISCORD_BOT_TOKEN,
            "GUILD_ID": settings.GUILD_ID,
            "SUBNET_CONFIG_URL": settings.SUBNET_CONFIG_URL,
            "BOT_NAME": settings.BOT_NAME,
            "CATEGORY_NAME": settings.CATEGORY_NAME,
        }
        self.logger: logging.Logger = logger
        self.config_manager = SubnetConfigManager(self, self.logger, self.config)
        self.category_creation_lock = asyncio.Lock()

        # Define intents
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        # Initialize the bot with the specified command prefix and intents
        super().__init__(command_prefix="!", intents=intents)
        self.logger.debug("DiscordBot initialized.")

        # Connect to Redis
        self.redis_client = redis.Redis(host="localhost", port=8379, db=0)

    async def start_bot(self) -> None:
        await self.start(self.config["DISCORD_BOT_TOKEN"])

    async def setup_hook(self) -> None:
        asyncio.create_task(self.listen_to_redis())

    async def listen_to_redis(self):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("bot_commands")
        while True:
            message = pubsub.get_message()
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                await self.handle_command(data)
            await asyncio.sleep(0.1)

    async def handle_command(self, data):
        action = data.get("action")
        if action == "send_message":
            subnet_codename = data["channel_name"]
            message = data["message"]
            realm = data["realm"]
            await self.send_message_to_channel(subnet_codename, message, realm)

    async def on_ready(self) -> None:
        """
        Called when the bot is connected and ready. Logs connection details.
        """

        self.logger.info(f"Bot connected as {self.user}")
        for guild in self.guilds:
            self.logger.info(f"Connected to guild: {guild.name}")
        await self.config_manager.update_config_and_synchronize.start()

    async def on_member_join(self, member: discord.Member) -> None:
        """
        Called when a new member joins a guild. Grants channel permissions based on the pending invite.
        """
        self.logger.info(f"Member {member.name} joined guild {member.guild.name}.")

        user_id = UserID(member.id)

        # Check if the user has a pending invite with a specific channel
        channels = await self._get_pending_user_channels(user_id)
        for channel in channels:
            if channel:
                # Grant the user permissions to the specified channel
                await self._grant_channel_permissions(user_id, channel)
                self.logger.info(f"Granted permissions to {member.name} for channel '{channel}'.")

        # Clean up the pending invite entry as it's no longer needed
        await self._remove_pending_user(user_id)

    async def _create_channel(self, guild: discord.Guild, channel_name: ChannelName) -> None:
        normalized_category_name = self.config["CATEGORY_NAME"].strip().lower()
        category = discord.utils.find(lambda c: c.name.strip().lower() == normalized_category_name, guild.categories)

        # If the category doesn't exist, create it
        if category is None:
            # Double-check inside the lock to prevent race conditions
            async with self.category_creation_lock:
                category = discord.utils.find(
                    lambda c: c.name.strip().lower() == normalized_category_name, guild.categories
                )
                if category is None:
                    self.logger.info(f"Category '{self.config['CATEGORY_NAME']}' not found. Creating new category.")
                    category = await guild.create_category(name=self.config["CATEGORY_NAME"])
                    self.logger.info(f"Category '{self.config['CATEGORY_NAME']}' created in guild {guild.name}.")

        # Overwriting default permissions for the channel to make it private
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=category)
        self.logger.info(f"Channel '{channel_name}' created in guild {guild.name}.")

    async def _archieve_channel(self, guild: discord.Guild, channel_name: ChannelName) -> None:
        archive_category = discord.utils.get(guild.categories, name="Archive")

        if not archive_category:
            self.logger.info("Archive category not found. Creating 'Archive' category.")
            archive_category = await guild.create_category("Archive", reason="Created for archiving unused channels.")

        channel = discord.utils.get(guild.text_channels, name=channel_name)

        if channel and self._is_bot_channel(channel_name) and channel.category != archive_category:
            self.logger.info(f"Channel '{channel_name}' is being moved to the 'Archive' category.")
            await channel.edit(
                category=archive_category, reason="Channel moved to Archive as it's not listed in the subnet config."
            )

    async def send_message_to_channel(self, subnet_codename: str, message: str, realm: str) -> None:
        await self.wait_until_ready()

        guild = await self._get_guild_or_raise(int(self.config["GUILD_ID"]))
        category = discord.utils.get(guild.categories, name=self.config["CATEGORY_NAME"])

        if category is None:
            self.logger.error(f"Category named '{self.config['CATEGORY_NAME']}' not found in guild '{guild.name}'")
            raise ValueError(f"Category named '{self.config['CATEGORY_NAME']}' not found in guild '{guild.name}'")

        channels = category.text_channels
        channel = await self._get_channel(channels, subnet_codename, realm)

        if channel is None:
            self.logger.error(f"Channel named '{channel.name}' not found in guild '{guild.name}'")
            raise ValueError(f"Channel named '{channel.name}' not found in guild '{guild.name}'")
        await channel.send(message)

    async def _get_channel(self, channels, subnet_codename, realm):
        prefix = "t" if realm == "testnet" else "d" if realm == "devnet" else ""
        pattern = re.compile(rf"^{prefix}\d{{3}}-{subnet_codename}$")

        for channel in channels:
            if pattern.match(channel.name):
                return channel

        return None

    async def _send_invite_link(self, user_id: UserID, channel_name: ChannelName) -> None:
        """
        Sends a one-time invite link to a user for a specific guild and channel.
        """

        guild = await self._get_guild_or_raise(int(self.config["GUILD_ID"]))

        channel: discord.TextChannel | None = discord.utils.get(guild.text_channels, name=channel_name)
        if channel is None:
            self.logger.error(f"Channel {channel_name} not found.")
            raise ValueError(f"Channel {channel_name} not found.")

        invite = await channel.create_invite(max_uses=1, unique=True)
        try:
            user: discord.User | None = await self.fetch_user(user_id)
            await user.send(f"Join the server using this invite link: {invite.url}")
            self.logger.info(f"Sent invite to {user.name}.")
        except discord.NotFound:
            self.logger.error(f"User with ID {user_id} not found.")
        except discord.HTTPException as e:
            self.logger.error(f"Failed to send invite: {e}")

    async def _grant_channel_permissions(self, user_id: UserID, channel_name: ChannelName) -> None:
        """
        Grants a user read and write permissions to a specified channel in a guild.
        """

        guild = await self._get_guild_or_raise(int(self.config["GUILD_ID"]))

        # Check if the user is already a member of the server
        member: discord.Member | None = guild.get_member(user_id)

        if member is None:
            self.logger.error(f"User with ID {user_id} is not in the server.")
            raise ValueError(f"User with ID {user_id} is not in the server.")

        # Find the channel by name
        channel: discord.TextChannel | None = discord.utils.get(guild.text_channels, name=channel_name)

        if channel is None:
            self.logger.error(f"Channel '{channel_name}' not found.")
            raise ValueError(f"Channel '{channel_name}' not found.")

        # Create a PermissionOverwrite object to grant permissions
        overwrite: discord.PermissionOverwrite = discord.PermissionOverwrite()
        overwrite.read_messages = True
        overwrite.send_messages = True

        # Apply the permissions to the user for the specified channel
        await channel.set_permissions(member, overwrite=overwrite)
        self.logger.info(f"Granted read/write permissions to {member.name} for channel '{channel_name}'.")
        await member.send(f"You have been granted access to the channel '{channel_name}'.")

    async def _send_invite_or_grant_permissions(self, user_id: UserID, channel_name: ChannelName):
        """
        Sends an invite link to a user if they are not a member of the server,
        or grants permissions to a user if they are already a member.
        """

        guild = await self._get_guild_or_raise(int(self.config["GUILD_ID"]))

        member: discord.Member | None = guild.get_member(user_id)
        pending_user_channels: list[ChannelName] = await self._get_pending_user_channels(user_id)
        if member is None and len(pending_user_channels) == 0:
            await self._add_pending_user(user_id, channel_name)
            await self._send_invite_link(user_id, channel_name)
        elif member is None:
            await self._add_pending_user(user_id, channel_name)
        else:
            await self._grant_channel_permissions(user_id, channel_name)

    async def _revoke_channel_permissions(self, user_id: UserID, channel_name: ChannelName):
        """
        Revokes permissions for a user in a specified channel in a guild.
        """

        guild = await self._get_guild_or_raise(int(self.config["GUILD_ID"]))

        # Check if the user is already a member of the server
        member: discord.Member | None = guild.get_member(user_id)

        if member is None:
            self.logger.error(f"User with ID {user_id} is not in the server.")
            raise ValueError(f"User with ID {user_id} is not in the server.")

        if member.name == self.config["BOT_NAME"]:
            return

        # Find the channel by name
        channel: discord.TextChannel | None = discord.utils.get(guild.text_channels, name=channel_name)

        if channel is None:
            self.logger.error(f"Channel '{channel_name}' not found.")
            raise ValueError(f"Channel '{channel_name}' not found.")

        # Create a PermissionOverwrite object to revoke permissions
        overwrite: discord.PermissionOverwrite = discord.PermissionOverwrite()
        overwrite.read_messages = False
        overwrite.send_messages = False

        # Revoke the permissions of the user for the specified channel
        await channel.set_permissions(member, overwrite=overwrite)
        self.logger.info(f"Revoked read/write permissions of {member.name} for channel '{channel_name}'.")
        await member.send(f"Yor access to the '{channel_name}' channel has been revoked.")

    def _is_bot_channel(self, channel_name: ChannelName) -> bool:
        bot_channel_regex = r"^[td]?\d{3}-[\S]+$"
        return re.match(bot_channel_regex, channel_name) is not None

    async def close(self):
        self.config_manager.update_config_and_synchronize.cancel()
        await super().close()

    async def _get_guild_or_raise(self, guild_id: int) -> discord.Guild:
        guild: discord.Guild | None = self.get_guild(guild_id)
        if guild is None:
            self.logger.error(f"Guild with ID {guild_id} not found.")
            raise ValueError(f"Guild with ID {guild_id} not found.")
        return guild

    async def _add_pending_user(self, user_id: UserID, channel_name: ChannelName):
        redis_key = f"pending_users:{user_id}"
        self.redis_client.sadd(redis_key, channel_name)

    async def _remove_pending_user(self, user_id: UserID):
        redis_key = f"pending_users:{user_id}"
        self.redis_client.delete(redis_key)

    async def _get_pending_user_channels(self, user_id: UserID) -> list[ChannelName]:
        redis_key = f"pending_users:{user_id}"
        channels = self.redis_client.smembers(redis_key)
        return [ChannelName(ch.decode("utf-8")) for ch in channels]

    async def __aenter__(self):
        self._bot_task = asyncio.create_task(self.start_bot())
        await asyncio.sleep(1)  # Small delay to ensure the bot is starting up
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        await self._bot_task


if __name__ == "__main__":
    logger = logging.getLogger("bot")
    bot: DiscordBot = DiscordBot(logger)
    asyncio.run(bot.start_bot())
