from ..models import Hotkey, SubnetSlot, ValidatorInstance


def get_subnets_by_hotkeys(hotkey_ss58, subnet_ids):
    try:
        hotkey = Hotkey.objects.get(hotkey=hotkey_ss58)
        subnet_slots = []
        for subnet_id in subnet_ids:
            if subnet_id[0] == "t":
                netuid = int(subnet_id[1:])
                subnet_slots.append(SubnetSlot.objects.filter(netuid=netuid, blockchain="testnet").first())
            else:
                netuid = int(subnet_id)
                subnet_slots.append(SubnetSlot.objects.filter(netuid=netuid, blockchain="mainnet").first())
            validators = ValidatorInstance.objects.filter(hotkey=hotkey, subnet_slot__in=subnet_slots).distinct()
    except ValidatorInstance.DoesNotExist:
        return None
    return [validator.subnet_slot.subnet for validator in validators]


def send_messages(subnets):
    for subnet in subnets:
        # send message to subnet operators
        pass
