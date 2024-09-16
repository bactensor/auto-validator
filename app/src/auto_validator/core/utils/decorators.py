import json
import time
from functools import wraps

import bittensor as bt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.response import Response

from auto_validator.core.models import Hotkey
from auto_validator.core.utils.utils import get_subnets_by_hotkeys, send_messages


def verify_signature_and_route_subnet(view_func):
    @wraps(view_func)
    def _wrapped_view(view, *args, **kwargs):
        try:
            request = view.request
            nonce = request.headers.get("Nonce")
            hotkey = request.headers.get("Hotkey")
            signature = request.headers.get("Signature")
            note = request.headers.get("Note")
            subnet_ids_str = request.headers.get("SubnetIDs")
            if subnet_ids_str:
                subnet_ids = [sn_id for sn_id in subnet_ids_str.split(",")]

            nonce_float = float(nonce)

            current_time = time.time()
            if abs(current_time - nonce_float) > int(settings.SIGNATURE_EXPIRE_DURATION):
                raise AuthenticationFailed("Invalid nonce")

            if not hotkey:
                raise PermissionDenied("Hotkey missing")

            if Hotkey.objects.get(hotkey=hotkey) is None:
                raise PermissionDenied("Invalid hotkey")

            method = request.method
            url = request.build_absolute_uri()
            headers = {
                "Note": note,
                "Nonce": nonce,
                "Hotkey": hotkey,
                "SubnetIDs": subnet_ids_str,
            }
            headers = json.dumps(headers, sort_keys=True)
            files = request.FILES["file"]
            file_content = files.read()
            keypair = bt.Keypair(ss58_address=hotkey)

            data_to_verify = f"{method}{url}{headers}{file_content}".encode()
            if not keypair.verify(data_to_verify, signature=bytes.fromhex(signature)):
                raise AuthenticationFailed("Invalid signature")

            subnets = get_subnets_by_hotkeys(hotkey, subnet_ids)
            if not subnets:
                raise ValidationError("Invalid hotkey")

            send_messages(subnets)

        except AuthenticationFailed as e:
            return Response({"detail": str(e)}, status=401)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=403)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=400)
        except Exception:
            return Response({"detail": "Invalid operation"}, status=500)

        return view_func(view, *args, **kwargs)

    return _wrapped_view
