import logging

import bittensor as bt
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from .models import SubnetSlot, ValidatorInstance

logger = logging.getLogger(__name__)


@shared_task
def update_validator_status():
    # Step 1: Get all subnet slots ordered by ID
    subnet_slots = SubnetSlot.objects.filter().order_by("id")
    total_slots = subnet_slots.count()

    if total_slots == 0:
        logger.warning("No subnet slots found.")
        return

    # Step 2: Get the current slot index from the cache (default to 0)
    current_index = cache.get("current_subnet_slot_index", 0)

    # Step 3: Get the next subnet slot to process
    slot = subnet_slots[current_index]
    blockchain = slot.blockchain
    netuid = slot.netuid
    bt.subtensor(network="finney")
    # Step 4: Process the selected slot
    try:
        subtensor = bt.subtensor(network=settings.BT_NETWORK_NAME)
        validators = ValidatorInstance.objects.filter(subnet_slot=slot)
        if validators.exists():
            metagraph = bt.metagraph(netuid=netuid, network="local", lite=True, sync=True)
            # current_block = subtensor.get_current_block()
            for validator in validators:
                last_updated = fetch_last_updated_from_metagraph(metagraph, validator.hotkey.hotkey)
                validator.last_updated = last_updated
                validator.save()
                logger.info(f"Validator:{validator.hotkey}, netuid:{netuid} was successfully updated!")
        else:
            logger.warning(f"No validators found for subnet slot with ID {slot.id}.")
    except Exception as e:
        logger.error(f"Failed to update validators for netuid {netuid} on {blockchain}: {e}")
    finally:
        subtensor.close()

    # Step 5: Update the index to point to the next slot
    next_index = (current_index + 1) % total_slots
    cache.set("current_subnet_slot_index", next_index)


def fetch_last_updated_from_metagraph(metagraph, public_key):
    return metagraph.last_update[metagraph.hotkeys.index(public_key)]
