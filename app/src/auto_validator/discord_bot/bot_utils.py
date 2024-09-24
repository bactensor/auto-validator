from django.conf import settings


def validate_bot_settings():
    required_settings = [
        "DISCORD_BOT_TOKEN",
        "GUILD_ID",
        "SUBNET_CONFIG_URL",
        "BOT_NAME",
        "CATEGORY_NAME"
    ]
    
    missing_settings = []
    for setting in required_settings:
        if not getattr(settings, setting, None):
            missing_settings.append(setting)
    
    if missing_settings:
        raise ValueError(f"Missing required bot settings: {', '.join(missing_settings)}")

