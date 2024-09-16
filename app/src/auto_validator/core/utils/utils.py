import difflib
import json

import requests
from django.conf import settings
from django.shortcuts import redirect, render

from ..models import Hotkey, Subnet, SubnetSlot, ValidatorInstance

GITHUB_URL = settings.SUBNETS_INFO_GITHUB_URL


def fetch_and_compare_subnets(request):
    response = requests.get(GITHUB_URL, timeout=30)
    if response.status_code != 200:
        return render(request, "admin/sync_error.html", {"error": "Failed to fetch data from GitHub."})

    github_data = response.json()
    db_data = list(Subnet.objects.values())

    github_data = [subnet for subnet in github_data.values()]
    db_data = [{k: v for k, v in subnet.items() if k != "id"} for subnet in db_data]
    github_data_str = json.dumps(github_data, indent=2, sort_keys=True)
    db_data_str = json.dumps(db_data, indent=2, sort_keys=True)

    diff = difflib.unified_diff(
        db_data_str.splitlines(), github_data_str.splitlines(), fromfile="db_data", tofile="github_data", lineterm=""
    )
    diff_str = "\n".join(diff)

    if request.method == "POST":
        new_data = list(github_data)
        for subnet_data in new_data:
            subnet, created = Subnet.objects.update_or_create(
                codename=subnet_data.get("codename"), defaults=subnet_data
            )
        return redirect("admin:core_subnet_changelist")

    return render(
        request,
        "admin/sync_subnets.html",
        {
            "diff_str": diff_str,
            "github_data": json.dumps(github_data),
        },
    )


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
