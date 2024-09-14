from collections.abc import Generator
from unittest import mock

import bittensor as bt
import pytest
import subprocess
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from auto_validator.core.models import Hotkey, Server, Subnet, SubnetSlot, ValidatorInstance


@pytest.fixture
def some() -> Generator[int, None, None]:
    # setup code
    yield 1
    # teardown code


@pytest.mark.django_db
@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="testuser", password="testpass")


@pytest.mark.django_db
@pytest.fixture
def auth_token(user):
    token, _ = Token.objects.get_or_create(user=user)
    return token


@pytest.mark.django_db
@pytest.fixture
def hotkey(wallet):
    hotkey, _ = Hotkey.objects.get_or_create(hotkey=wallet.hotkey.ss58_address)
    return hotkey


@pytest.mark.django_db
@pytest.fixture
def subnet():
    subnet = Subnet.objects.create(name="test_subnet")
    return subnet


@pytest.mark.django_db
@pytest.fixture
def subnet_slot(subnet):
    subnet_slot = SubnetSlot.objects.create(subnet=subnet, netuid=1)
    return subnet_slot


@pytest.mark.django_db
@pytest.fixture
def server():
    server = Server.objects.create(name="test_server", ip_address="127.0.0.1")
    return server


@pytest.mark.django_db
@pytest.fixture
def validator_instance(subnet_slot, server, hotkey):
    validator_instance = ValidatorInstance.objects.create(subnet_slot=subnet_slot, server=server, hotkey=hotkey)
    return validator_instance


@pytest.fixture
def api_client():
    client = APIClient()
    return client


@pytest.fixture
def eq():
    class EqualityMock:
        def __init__(self, func):
            self.func = func

        def __eq__(self, other):
            return self.func(other)

    return EqualityMock


@pytest.fixture
def wallet():
    process = subprocess.Popen(
        ['python3', '-c', f'import bittensor as bt; wallet = bt.wallet(name="test_wallet", hotkey="testhotkey"); wallet.create_if_non_existent()'],
        stdin=subprocess.PIPE,
        text=True
    )
    process.communicate(input="123123123")
    wallet = bt.wallet(name="test_wallet", hotkey="testhotkey")
    wallet.create_if_non_existent()
    return wallet
