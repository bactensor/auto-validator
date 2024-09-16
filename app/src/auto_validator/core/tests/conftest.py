from collections.abc import Generator

import bittensor as bt
import pexpect
import pytest
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
    coldkey_name = "auto-validator6"
    command1 = f"btcli wallet new_coldkey --wallet.name {coldkey_name}"
    command2 = f"btcli wallet new_hotkey --wallet.name {coldkey_name} --wallet.hotkey testhotkey5"
    has_coldkey = False
    has_hotkey = False
    password = "your_password_here"  # Securely handle the password

    try:
        wallet = bt.wallet(name=coldkey_name, hotkey="testhotkey5")
        wallet.coldkeypub
        has_coldkey = True
        wallet.hotkey
        has_hotkey = True
    except bt.KeyFileError:
        if not has_coldkey:
            process = pexpect.spawn(command1, timeout=500)  # Adjust timeout as needed
            try:
                process.expect("Specify password for key encryption:")
                process.sendline(password)

                process.expect("Retype your password:")
                process.sendline(password)

                # Handle file already exists prompt
                process.expect("File .* already exists. Overwrite? (y/N) ")
                process.sendline("y")

                process.expect(pexpect.EOF)  # Wait until the command finishes
            except pexpect.TIMEOUT:
                print("Timeout occurred while creating coldkey.")
            finally:
                process.close()

        if not has_hotkey:
            process = pexpect.spawn(command2, timeout=500)  # Adjust timeout as needed
            try:
                process.expect(pexpect.EOF)  # Wait until the command finishes
            except pexpect.TIMEOUT:
                print("Timeout occurred while creating hotkey.")
            finally:
                process.close()
        # Load the wallet again after creation
        wallet = bt.wallet(name=coldkey_name, hotkey=coldkey_name)

    return wallet
