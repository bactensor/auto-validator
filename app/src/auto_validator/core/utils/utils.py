from ..models import Hotkey, ValidatorInstance


def get_subnets_by_hotkeys(hotkey_ss58):
    try:
        hotkey = Hotkey.objects.get(hotkey=hotkey_ss58)
        validators = ValidatorInstance.objects.filter(hotkey=hotkey)
    except ValidatorInstance.DoesNotExist:
        return None
    return [validator.subnet_slot.subnet for validator in validators]


def send_messages(subnets):
    for subnet in subnets:
        # send message to subnet operators
        pass
