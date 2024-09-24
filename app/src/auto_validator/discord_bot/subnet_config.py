import asyncio
import logging
from typing import Any, Literal, NewType

import aiohttp
import discord
from discord.ext import tasks
from pydantic import BaseModel, Field, ValidationError, field_validator

ChannelName = NewType("ChannelName", str)
UserID = NewType('UserID', int)

class DiscordSubnetConfig(BaseModel):
    maintainers_ids: list[UserID] = Field(
        ...,
        min_length=1,
        description="List of maintainer IDs, each must be an 18-digit integer"
    )
    subnet_codename: str = Field(..., min_length=1)
    netuid: int = Field(..., ge=0, le=32767)
    realm: Literal["testnet", "mainnet", "devnet"] = Field(...)

    @field_validator('maintainers_ids', mode='before')
    def validate_maintainer_ids(cls, users):
        if not isinstance(users, list):
            raise ValueError('maintainers_ids must be a list')
        
        for user in users:
            if not isinstance(user, int) or len(str(user)) < 18:
                raise ValueError('Each maintainer ID must be at least 18-digit integer')
        return users

    def generate_channel_name(self) -> ChannelName:
        prefix = "t" if self.realm == "testnet" else "d" if self.realm == "devnet" else ""
        return f"{prefix}{self.netuid:03d}-{self.subnet_codename}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.subnet_codename}, {self.netuid}, {self.realm})"


class DiscordSubnetConfigFactory:
    _used_realm_netuid_pairs: set[tuple[str, int]] = set()

    @classmethod
    def reset_state(cls):
        cls._used_realm_netuid_pairs.clear()

    def validate_unique(subnet: DiscordSubnetConfig) -> None:  
        if (realm_netuid_pair := (subnet.realm, subnet.netuid)) in DiscordSubnetConfigFactory._used_realm_netuid_pairs:
            raise ValueError(f"The combination of realm '{subnet.realm}' and netuid '{subnet.netuid}' must be unique.")
        
        DiscordSubnetConfigFactory._used_realm_netuid_pairs.add(realm_netuid_pair)

    @classmethod
    def get_subnets_config(cls, logger: logging.Logger, config_data: dict) -> list[DiscordSubnetConfig]:
        subnets = []
        for subnet_config in config_data.get('subnets', []):
            try:
                subnet = DiscordSubnetConfig(**subnet_config)
                cls.validate_unique(subnet)
                subnets.append(subnet)
            except (ValidationError, ValueError) as e:
                logger.exception(f"Validation error for subnet {subnet_config.get('subnet_codename', 'unknown')}: {e}")
                raise

        return subnets

class SubnetConfigManager:
    """
        This class provides functionality for updating the config
          and synchronizing it with the discord server state
    """
    def __init__(self, bot: discord.Client, logger: logging.Logger, config: dict[str, Any]):
        self.bot = bot
        self.config = config
        self.logger = logger
        self.subnets_config: list[DiscordSubnetConfig]

    @tasks.loop(minutes=10)  # Adjust the interval as needed
    async def update_config_and_synchronize(self) -> None:
        """
        Periodically updates the configuration from remote repo and synchronizes the Discord server.
        """
        self.logger.info("Updating configuration and synchronizing Discord server...")
        
        try:
            await self.load_config_from_remote_repo()
            await self.synchronize_discord_with_subnet_config()
            self.logger.info("Synchronization complete.")
            DiscordSubnetConfigFactory.reset_state()
        except Exception:
            self.logger.exception("Unexpected error during remote repo synchronization")

    async def load_config_from_remote_repo(self) -> None:
        """
        Fetches the configuration from a remote GitHub repository.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(self.config["SUBNET_CONFIG_URL"]) as response:
                if response.status == 200:
                    json_config = await response.json()
                    try:
                        self.subnets_config = DiscordSubnetConfigFactory.get_subnets_config(self.logger, json_config)
                        self.logger.info("Configuration fetched and processed successfully.")
                    except (ValidationError, ValueError) as e:
                        self.logger.exception(f"Configuration processing failed: {e}")
                        raise
                else:
                    self.logger.error(f"Failed to fetch configuration. Status code: {response.status}")
                    raise ValueError("Could not fetch configuration from remote repo.")
                
    async def synchronize_discord_with_subnet_config(self) -> None:
        """
        Synchronizes the Discord server's users and channels with the subnet config from the remote repo:
        - Invites users that are not yet on the server but listed in the config.
        - Revokes users access if their ID is not listed on subnet config.
        - Creates channels that are not yet on the server but listed in the config.
        - Archives channels that are on the server but not listed in the config.
        """

        guild = await self.bot._get_guild_or_raise(int(self.config["GUILD_ID"]))

        current_channels_users_mapping = self.get_current_channel_user_mapping(guild)
        desired_channels_to_users_mapping = self.get_desired_channel_user_mapping()

        missing_channels, channels_to_archieve = self.determine_missing_and_unnecessary_channels(current_channels_users_mapping.keys(),
                                                                                                desired_channels_to_users_mapping.keys())
        tasks = [
            *(self.bot._archieve_channel(guild, channel_name) for channel_name in channels_to_archieve),
            *(self.bot._create_channel(guild, channel_name) for channel_name in missing_channels)
        ]

        await asyncio.gather(*tasks)

        tasks = []
        updated_channels_to_users_mapping = self.get_current_channel_user_mapping(guild)
        for channel_name, desired_maintainer_ids in desired_channels_to_users_mapping.items():
            missing_users, users_to_remove = self.determine_missing_and_unnecessary_users(
                set(updated_channels_to_users_mapping[channel_name]), set(desired_maintainer_ids))
            tasks.extend(self.bot._send_invite_or_grant_permissions(user, channel_name) for user in missing_users)
            tasks.extend(self.bot._revoke_channel_permissions(member_id, channel_name) for member_id in users_to_remove)

        await asyncio.gather(*tasks)

    def get_current_channel_user_mapping(self, guild: discord.Guild) -> dict[ChannelName, list[UserID]]:
        channels_to_users = {}
        for channel in guild.text_channels:
            if self.bot._is_bot_channel(channel.name):
                users_in_channel = [
                    UserID(member.id)
                    for member in channel.members
                    if channel.permissions_for(member).view_channel
                ]
                channels_to_users[ChannelName(channel.name)] = users_in_channel
        return channels_to_users
    
    def get_desired_channel_user_mapping(self) -> dict[ChannelName, list[UserID]]:
        channels_to_users = {}
        for subnet_config in self.subnets_config:
            channel_name = subnet_config.generate_channel_name()
            channels_to_users[channel_name] = subnet_config.maintainers_ids
        return channels_to_users

    def determine_missing_and_unnecessary_users(self, current_member_ids: set[UserID], desired_member_ids: set[UserID]) -> tuple[set[UserID], set[UserID]]:
        missing_users = desired_member_ids - current_member_ids
        users_to_remove = current_member_ids - desired_member_ids
        return missing_users, users_to_remove
    
    def determine_missing_and_unnecessary_channels(self, current_channel_names: set[ChannelName], desired_channel_names: set[ChannelName]) -> tuple[set[ChannelName], set[ChannelName]]:
        missing_channels = desired_channel_names - current_channel_names
        channels_to_archieve = current_channel_names - desired_channel_names
        return missing_channels, channels_to_archieve