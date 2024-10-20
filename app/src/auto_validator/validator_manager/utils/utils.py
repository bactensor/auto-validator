import logging

import requests
from django.conf import settings
from django.db import transaction

from ..models import ExternalHotkey, Subnet, Validator, ValidatorHotkey

logger = logging.getLogger(__name__)

GITHUB_VALIDATORS_CONFIG_PATH = settings.GITHUB_VALIDATORS_CONFIG_PATH


def sync_validators():
    try:
        response = requests.get(GITHUB_VALIDATORS_CONFIG_PATH, timeout=30)
        if response.status_code != 200:
            raise Exception("Failed to fetch data from GitHub.")

        github_data = response.json()
        github_validators = []

        for validator_short_name, validator_info in github_data.items():
            github_validators.append(
                {
                    "short_name": validator_short_name,
                    "long_name": validator_info.get("long_name"),
                    "last_stake": validator_info.get("last_stake"),
                    "default_hotkey": validator_info.get("default_hotkey"),
                    "subnet_hotkeys": validator_info.get("subnet_hotkeys", {}),
                }
            )

        with transaction.atomic():
            for validator_data in github_validators:
                validator, _ = Validator.objects.update_or_create(
                    long_name=validator_data["long_name"],
                    short_name=validator_data["short_name"],
                    defaults={
                        "last_stake": validator_data["last_stake"],
                    },
                )

                # Handle Default Hotkey
                default_hotkey_hk = validator_data.get("default_hotkey")
                if default_hotkey_hk:
                    external_hotkey_default, _ = ExternalHotkey.objects.get_or_create(
                        hotkey=default_hotkey_hk,
                        defaults={
                            "name": f"{validator_data['short_name']}-default",
                            "subnet": None,  # Default hotkey is not linked to a subnet
                        },
                    )

                    current_default_hotkey = validator.default_hotkey
                    ValidatorHotkey.objects.update_or_create(
                        validator=validator, external_hotkey=external_hotkey_default, defaults={"is_default": True}
                    )

                    # Remove old default hotkey if it's different
                    if current_default_hotkey and current_default_hotkey != external_hotkey_default:
                        ValidatorHotkey.objects.filter(
                            validator=validator, external_hotkey=current_default_hotkey, is_default=True
                        ).delete()

                else:
                    # If no default_hotkey in GitHub data, remove existing default if any
                    ValidatorHotkey.objects.filter(validator=validator, is_default=True).delete()

                # Handle Subnet Hotkeys
                associated_subnets = []
                subnet_hotkeys = validator_data.get("subnet_hotkeys", {})

                for subnet_codename, hotkeys in subnet_hotkeys.items():
                    subnet, _ = Subnet.objects.get_or_create(
                        codename=subnet_codename, defaults={"codename": subnet_codename}
                    )

                    associated_subnets.append(subnet)

                    for idx, hk in enumerate(hotkeys):
                        extension = f"[{idx}]" if idx > 0 else ""
                        external_hotkey, _ = ExternalHotkey.objects.get_or_create(
                            hotkey=hk,
                            defaults={
                                "name": f"{validator_data['short_name']}-{subnet.codename}{extension}",
                                "subnet": subnet,
                            },
                        )
                        ValidatorHotkey.objects.update_or_create(
                            validator=validator, external_hotkey=external_hotkey, defaults={"is_default": False}
                        )

                # Set the associated subnets
                if associated_subnets:
                    validator.subnets.set(associated_subnets)
                else:
                    validator.subnets.clear()

                # Remove non-default hotkeys not present in GitHub data
                existing_hk = ValidatorHotkey.objects.filter(validator=validator, is_default=False)
                desired_hk = set(hk for hotkeys in subnet_hotkeys.values() for hk in hotkeys)
                for hk_instance in existing_hk:
                    if hk_instance.external_hotkey.hotkey not in desired_hk:
                        hk_instance.external_hotkey.delete()

        logger.info("Validators synchronization completed successfully.")

    except Exception as e:
        logger.exception(f"An error occurred during Validators synchronization: {str(e)}")
        raise
