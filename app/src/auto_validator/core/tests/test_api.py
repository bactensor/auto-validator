import io
import json
import re
import time

import pytest
from rest_framework import status

from auto_validator.core.models import Hotkey, UploadedFile

V1_FILES_URL = "/api/v1/files/"


@pytest.mark.django_db
def test_file_upload_with_valid_signature(api_client, wallet, validator_instance):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }

    headers = {}
    headers["Note"] = ""
    headers["SubnetID"] = "1"
    headers["Realm"] = "testserver"
    headers["Nonce"] = str(time.time())
    headers["Hotkey"] = wallet.hotkey.ss58_address
    headers_str = json.dumps(headers, sort_keys=True)
    decoded_file_content = file_content.read().decode(errors="ignore")
    data_to_sign = f"POSThttp://testserver{V1_FILES_URL}{headers_str}{decoded_file_content}".encode()
    file_content.seek(0)
    signature = wallet.hotkey.sign(
        data_to_sign,
    ).hex()
    headers["Signature"] = signature
    response = api_client.post(V1_FILES_URL, file_data, format="multipart", headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["file_name"] == "testfile.txt"
    assert response_data["file_size"] == 12
    assert response_data["description"] == ""
    assert re.match(
        r"^http://testserver/media/"
        + validator_instance.subnet_slot.subnet.name
        + r"-"
        + str(validator_instance.subnet_slot.netuid)
        + r"-"
        + wallet.hotkey.ss58_address
        + r"-.*-testfile.txt$",
        response_data["url"],
    )

    assert UploadedFile.objects.count() == 1
    uploaded_file = UploadedFile.objects.first()
    assert uploaded_file.file_name == "testfile.txt"
    assert uploaded_file.description == ""
    assert uploaded_file.hotkey.hotkey == wallet.hotkey.ss58_address
    assert uploaded_file.file_size == 12


@pytest.mark.django_db
def test_file_upload_with_invalid_signature(api_client, wallet, validator_instance):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }
    headers = {}
    headers["Note"] = ""
    headers["SubnetID"] = "1"
    headers["Realm"] = "testserver"
    headers["Nonce"] = str(time.time())
    headers["Hotkey"] = wallet.hotkey.ss58_address
    headers["Signature"] = "invalid_signature"
    response = api_client.post(V1_FILES_URL, file_data, format="multipart", headers=headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED or status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
def test_file_upload_with_missing_hotkey(api_client):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }
    headers = {}
    headers["Note"] = ""
    headers["SubnetID"] = "1"
    headers["Realm"] = "testserver"
    headers["Nonce"] = str(time.time())
    headers["Hotkey"] = ""
    headers["Signature"] = "invalid_signature"
    response = api_client.post(V1_FILES_URL, file_data, format="multipart", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_file_upload_with_invalid_hotkey(api_client, wallet):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }
    headers = {}
    headers["Note"] = ""
    headers["SubnetID"] = "1"
    headers["Realm"] = "testserver"
    headers["Nonce"] = str(time.time())
    headers["Hotkey"] = "123"
    headers["Signature"] = "invalid_signature"
    response = api_client.post(V1_FILES_URL, file_data, format="multipart", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_files(api_client, hotkey):
    UploadedFile.objects.create(file_name="file1.txt", file_size=1, hotkey=hotkey, storage_file_name="file1.txt")
    UploadedFile.objects.create(file_name="file2.txt", file_size=2, hotkey=hotkey, storage_file_name="file2.txt")

    another_hotkey = Hotkey.objects.create(hotkey="another_hotkey")
    UploadedFile.objects.create(
        file_name="file3.txt", file_size=3, hotkey=another_hotkey, storage_file_name="file3.txt"
    )

    response = api_client.get(V1_FILES_URL, headers={"Hotkey": hotkey.hotkey, "Note": ""})

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["file_name"] == "file1.txt"
    assert response_data[0]["file_size"] == 1
    assert response_data[0]["description"] == ""
    assert re.match(r"^http://testserver/media/file1.txt$", response_data[0]["url"])
    assert response_data[1]["file_name"] == "file2.txt"
    assert response_data[1]["file_size"] == 2
    assert response_data[1]["description"] == ""
    assert re.match(r"^http://testserver/media/file2.txt$", response_data[1]["url"])


@pytest.mark.django_db
def test_list_files_empty(api_client):
    response = api_client.get(V1_FILES_URL, headers={"Hotkey": ""})
    assert (response.status_code, response.json()) == (status.HTTP_200_OK, [])
