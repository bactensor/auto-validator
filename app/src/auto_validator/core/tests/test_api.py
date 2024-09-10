import io
from datetime import datetime
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from auto_validator.core.models import UploadedFile

V1_FILES_URL = "/api/v1/files/"


@mock.patch("auto_validator.core.utils.decorators.verify_signature_and_route_subnet", lambda x: x)
@pytest.mark.django_db
def test_file_upload_with_valid_signature(api_client, user, eq):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }
    response = api_client.post(V1_FILES_URL, file_data, format="multipart")

    assert (response.status_code, response.json()) == (
        status.HTTP_201_CREATED,
        {
            "created_at": eq(lambda x: bool(datetime.fromisoformat(x))),
            "description": "",
            "file_name": "testfile.txt",
            "file_size": 12,
            "id": user.id,
            "url": eq(lambda x: x.startswith("/media/1-") and x.endswith("testfile.txt")),
        },
    )
    assert UploadedFile.objects.count() == 1
    uploaded_file = UploadedFile.objects.first()
    assert uploaded_file.file_name == "testfile.txt"
    assert uploaded_file.description == ""
    assert uploaded_file.user.username == user.username
    assert uploaded_file.file_size == 12


@pytest.mark.django_db
def test_file_upload_with_invalid_signature(api_client, user):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }

    with mock.patch(
        "auto_validator.core.utils.decorators.verify_signature_and_route_subnet",
        side_effect=PermissionDenied("Invalid signature"),
    ):
        with pytest.raises(PermissionDenied):
            api_client.post(V1_FILES_URL, file_data, format="multipart")

    assert UploadedFile.objects.count() == 0


@pytest.mark.django_db
def test_list_files(api_client, user, django_user_model, eq):
    UploadedFile.objects.create(file_name="file1.txt", file_size=1, user=user, storage_file_name="file1.txt")
    UploadedFile.objects.create(file_name="file2.txt", file_size=2, user=user, storage_file_name="file2.txt")

    another_user = django_user_model.objects.create_user(username="another_user", password="testpass")
    UploadedFile.objects.create(file_name="file3.txt", file_size=3, user=another_user, storage_file_name="file3.txt")

    response = api_client.get(V1_FILES_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "created_at": eq(lambda x: bool(datetime.fromisoformat(x))),
            "description": "",
            "file_name": "file1.txt",
            "file_size": 1,
            "id": eq(lambda x: isinstance(x, int)),
            "url": "/media/file1.txt",
        },
        {
            "created_at": eq(lambda x: bool(datetime.fromisoformat(x))),
            "description": "",
            "file_name": "file2.txt",
            "file_size": 2,
            "id": eq(lambda x: isinstance(x, int)),
            "url": "/media/file2.txt",
        },
    ]


@pytest.mark.django_db
def test_list_files_empty(api_client):
    response = api_client.get(V1_FILES_URL)
    assert (response.status_code, response.json()) == (status.HTTP_200_OK, [])
