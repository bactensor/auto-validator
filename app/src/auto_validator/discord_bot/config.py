"""
This module loads and validates configuration settings from environment variables 
for a Discord bot. Environment variables are loaded from a `.env` file
that is supposed to be located in the project's root directory.
"""

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


def load_config() -> Dict[str, str]:
    """
    Loads and validates environment variables from a .env file.
    """

    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    config: Dict[str, str] = {
        "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN"),
        "GUILD_ID": os.getenv("GUILD_ID"),
        "SUBNET_CONFIG_URL": os.getenv("SUBNET_CONFIG_URL"),
        "BOT_NAME": os.getenv("BOT_NAME"),
        "CATEGORY_NAME": os.getenv("CATEGORY_NAME"),
        # Add more configuration options as needed
    }

    # Validate that all required environment variables are set
    required_vars = ["DISCORD_BOT_TOKEN", "GUILD_ID", "SUBNET_CONFIG_URL", "BOT_NAME", "CATEGORY_NAME"]
    for var in required_vars:
        if config[var] is None:
            raise ValueError(f"Environment variable {var} is not set")

    return config

