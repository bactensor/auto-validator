import difflib
import json

import requests
from django.conf import settings
from django.shortcuts import redirect, render

from ..models import Hotkey, Server, Subnet, ValidatorInstance

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


def get_subnet_by_hotkey(hotkey_ss58, ip_address):
    try:
        hotkey = Hotkey.objects.get(hotkey=hotkey_ss58)
        server = Server.objects.get(ip_address=ip_address)
        validator = ValidatorInstance.objects.get(hotkey=hotkey, server=server)
    except ValidatorInstance.DoesNotExist:
        return None
    return validator.subnet_slot.subnet


def send_messages(subnet, subnet_identifier):
    """
    This function sends messages to subnet operators.
    Args:   subnet: Subnet object
            subnet_identifier: SubnetID
    """
    # send message to subnet operators
    pass


def get_user_ip(request):
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip_address:
        ip_address = ip_address.split(",")[0]
    else:
        ip_address = request.META.get("REMOTE_ADDR")
    return ip_address
