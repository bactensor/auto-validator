import time
from unittest.mock import Mock, patch

import pytest
from rest_framework.response import Response

from auto_validator.core.utils.decorators import verify_signature_and_route_subnet


@patch("auto_validator.core.utils.decorators.bt.Keypair")
@patch("auto_validator.core.utils.decorators.get_subnets_by_hotkeys")
@patch("auto_validator.core.utils.decorators.send_messages")
@pytest.mark.django_db
def test_valid_signature(mock_send_messages, mock_get_subnets_by_hotkeys, mock_keypair):
    mock_get_subnets_by_hotkeys.return_value = ["subnet1"]
    mock_keypair.return_value.verify.return_value = True

    @verify_signature_and_route_subnet
    def mock_view(view, *args, **kwargs):
        return Response({"detail": "Success"}, status=200)

    request = Mock()
    request.headers = {
        "Nonce": str(time.time()),
        "Hotkey": "5GHbqzeqBBVkBjA94N4Hq2ar4WSRKFGyWWBzkWuWpn8v1vZu",
        "Signature": "d470af4f62165069982c8fc6ef4606c962aa0ec8e39ed031d1faee3aabc26467cb4c115318040fbb066129691e1ef5eb2a480367640ff888149bf7653f790280",
        "Authorization": "Token 2920141af1f81b1d41b0ca3d6a170f3122e47909",
    }
    request.method = "POST"
    request.build_absolute_uri.return_value = "http://testserver/test"
    request.FILES = {"file": Mock()}
    request.FILES["file"].read.return_value = b"file_content"

    view = Mock()
    view.request = request

    response = mock_view(view)
    assert response.status_code == 200
    assert response.data == {"detail": "Success"}
