import json
import time
from functools import wraps

import bittensor as bt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.response import Response

from auto_validator.core.utils.utils import get_subnets_by_hotkeys, send_messages


def verify_signature_and_route_subnet(view_func):
    @wraps(view_func)
    def _wrapped_view(view, *args, **kwargs):
        try:
            request = view.request
            nonce = request.headers.get("Nonce")
            hotkey = request.headers.get("Hotkey")
            signature = request.headers.get("Signature")
            authorization = request.headers.get("Authorization")

            nonce_float = float(nonce)

            current_time = time.time()
            if abs(current_time - nonce_float) > int(settings.SIGNATURE_EXPIRE_DURATION):
                raise AuthenticationFailed("Invalid nonce")

            if not hotkey:
                raise PermissionDenied("Hotkey missing")

            method = request.method
            url = request.build_absolute_uri()
            headers = {
                "Authorization": authorization,
                "Nonce": nonce,
                "Hotkey": hotkey,
            }
            headers = json.dumps(headers, sort_keys=True)
            files = request.FILES["file"]
            file_content = files.read()
            keypair = bt.Keypair(ss58_address=hotkey)

            data_to_verify = f"{method}{url}{headers}{file_content}".encode()
            if not keypair.verify(data_to_verify, signature=bytes.fromhex(signature)):
                raise ValidationError("Invalid signature")

            subnets = get_subnets_by_hotkeys(hotkey)
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
