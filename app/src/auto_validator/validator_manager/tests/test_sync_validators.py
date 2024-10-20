from unittest.mock import patch

import pytest
from django.db import IntegrityError
from requests.exceptions import RequestException

from auto_validator.validator_manager.models import ExternalHotkey, Subnet, Validator, ValidatorHotkey
from auto_validator.validator_manager.tasks import sync_validators


def generate_hotkey(prefix, index):
    base = f"{prefix}_{index}"
    padding_length = 48 - len(base)
    return base + ("0" * padding_length)


@pytest.fixture(autouse=True)
def clear_db():
    # Clear models before each test
    Validator.objects.all().delete()
    Subnet.objects.all().delete()
    ExternalHotkey.objects.all().delete()
    ValidatorHotkey.objects.all().delete()


@pytest.mark.django_db(transaction=True)
@patch("requests.get")
def test_sync_validators_with_valid_data(mock_get):
    mock_response_data = {
        "validator1": {
            "long_name": "Validator One",
            "last_stake": 1000,
            "default_hotkey": generate_hotkey("hk_default", 1),
            "subnet_hotkeys": {
                "subnet1": [generate_hotkey("hk_subnet1", 1), generate_hotkey("hk_subnet1", 2)],
                "subnet2": [generate_hotkey("hk_subnet2", 1)],
            },
        },
        "validator2": {"long_name": "Validator Two", "last_stake": 2000, "default_hotkey": None, "subnet_hotkeys": {}},
    }

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response_data

    sync_validators()

    validator1 = Validator.objects.get(short_name="validator1")
    assert validator1.long_name == "Validator One"
    assert validator1.last_stake == 1000
    assert validator1.default_hotkey is not None
    assert validator1.default_hotkey.hotkey == generate_hotkey("hk_default", 1)
    assert validator1.subnets.count() == 2

    validator2 = Validator.objects.get(short_name="validator2")
    assert validator2.long_name == "Validator Two"
    assert validator2.last_stake == 2000
    assert validator2.default_hotkey is None
    assert validator2.subnets.count() == 0

    subnet1 = Subnet.objects.get(codename="subnet1")
    subnet2 = Subnet.objects.get(codename="subnet2")
    assert subnet1 in validator1.subnets.all()
    assert subnet2 in validator1.subnets.all()

    external_hotkeys = ExternalHotkey.objects.filter(validatorhotkey__validator=validator1)
    expected_hotkeys = {
        generate_hotkey("hk_default", 1),
        generate_hotkey("hk_subnet1", 1),
        generate_hotkey("hk_subnet1", 2),
        generate_hotkey("hk_subnet2", 1),
    }
    actual_hotkeys = set(external_hotkeys.values_list("hotkey", flat=True))
    assert actual_hotkeys == expected_hotkeys


@pytest.mark.django_db(transaction=True)
@patch("requests.get")
def test_sync_validators_removes_old_hotkeys(mock_get):
    old_hotkey_value = generate_hotkey("old_hotkey", 1)
    new_hotkey_value = generate_hotkey("new_hotkey", 1)
    default_hotkey_value = generate_hotkey("default_hotkey", 1)

    validator = Validator.objects.create(long_name="Validator One", short_name="validator1", last_stake=500)
    subnet = Subnet.objects.create(codename="subnet1")
    old_hotkey = ExternalHotkey.objects.create(hotkey=old_hotkey_value, name="validator1-subnet1", subnet=subnet)
    ValidatorHotkey.objects.create(validator=validator, external_hotkey=old_hotkey, is_default=False)
    validator.subnets.add(subnet)

    mock_response_data = {
        "validator1": {
            "long_name": "Validator One",
            "last_stake": 1000,
            "default_hotkey": default_hotkey_value,
            "subnet_hotkeys": {"subnet1": [new_hotkey_value]},
        }
    }

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response_data

    sync_validators()

    validator.refresh_from_db()

    assert validator.last_stake == 1000
    assert not ExternalHotkey.objects.filter(hotkey=old_hotkey_value).exists()
    assert ExternalHotkey.objects.filter(hotkey=new_hotkey_value).exists()
    assert validator.default_hotkey.hotkey == default_hotkey_value


@pytest.mark.django_db
@patch("requests.get")
def test_sync_validators_fetch_failure(mock_get):
    mock_get.side_effect = RequestException("Network error")

    with pytest.raises(Exception) as exc_info:
        sync_validators()

    assert "Network error" in str(exc_info.value)
    assert Validator.objects.count() == 0


@pytest.mark.django_db
@patch("requests.get")
def test_sync_validators_invalid_data_missing_fields(mock_get):
    mock_response_data = {
        "validator1": {
            # "long_name" is missing
            "last_stake": 1000,
            "default_hotkey": None,
            "subnet_hotkeys": {},
        },
        "validator2": {
            "long_name": "Validator Two",
            # "last_stake" is missing
            "default_hotkey": None,
            "subnet_hotkeys": {},
        },
    }

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response_data

    with pytest.raises(Exception) as exc_info:
        sync_validators()

    assert "null value in column" in str(exc_info.value)
    assert Validator.objects.count() == 0


@pytest.mark.django_db
@patch("requests.get")
def test_sync_validators_atomic_failure(mock_get):
    # Initial database state
    Validator.objects.create(long_name="Validator Before", short_name="validator_before", last_stake=500)

    mock_response_data = {
        "validator_new": {
            "long_name": "Validator New",
            "last_stake": 1000,
            "default_hotkey": None,
            "subnet_hotkeys": {},
        }
    }

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response_data

    with patch("auto_validator.validator_manager.models.Validator.objects.update_or_create") as mock_update_or_create:
        mock_update_or_create.side_effect = IntegrityError("Forced IntegrityError")

        with pytest.raises(Exception) as exc_info:
            sync_validators()

        assert "Forced IntegrityError" in str(exc_info.value)

    # Ensure database state is unchanged
    assert Validator.objects.filter(short_name="validator_before").exists()
    assert not Validator.objects.filter(short_name="validator_new").exists()
