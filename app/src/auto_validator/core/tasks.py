import bittensor as bt
import structlog
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from auto_validator.celery import app

from .models import SubnetSlot, ValidatorInstance

logger = structlog.wrap_logger(get_task_logger(__name__))


@app.task
def demo_task(x, y):
    logger.info("adding two numbers", x=x, y=y)
    return x + y


@app.task
def schedule_update_validator_status():
    subnet_slots = SubnetSlot.objects.order_by("id")
    for slot in subnet_slots:
        update_validator_status_for_slot.delay(slot.id)


@shared_task
def update_validator_status_for_slot(slot_id):
    try:
        slot = SubnetSlot.objects.get(id=slot_id)
    except SubnetSlot.DoesNotExist:
        logger.warning(f"Subnet slot with ID {slot_id} does not exist.")
        return

    try:
        subtensor = bt.subtensor(network=settings.BT_NETWORK_NAME)
        validators = ValidatorInstance.objects.filter(subnet_slot=slot)
        if validators.exists():
            metagraph = subtensor.metagraph(netuid=slot.netuid, lite=True)
            current_block = subtensor.get_current_block()
            for validator in validators:
                last_updated = fetch_last_updated_from_metagraph(metagraph, validator.hotkey.hotkey)
                validator.last_updated = current_block - last_updated
                validator.save()
                logger.info(f"Validator:{validator.hotkey}, subnet slot:{slot} was successfully updated!")
        else:
            logger.warning(f"No validators found for subnet slot with ID {slot.id}.")
    except Exception:
        logger.exception("Failed to update validators for subnet slot on %s", slot)
    finally:
        subtensor.close()


def fetch_last_updated_from_metagraph(metagraph, public_key):
    return metagraph.last_update[metagraph.hotkeys.index(public_key)]
