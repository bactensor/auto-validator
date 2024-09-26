import io
from datetime import datetime

import pytest
from rest_framework import status

from auto_validator.core.models import UploadedFile

V1_FILES_URL = "/api/v1/files/"


def test_file_upload(api_client, eq):
    file_content = io.BytesIO(b"file content")
    file_content.name = "testfile.txt"

    file_data = {
        "file": file_content,
    }
    response = api_client.post(V1_FILES_URL, file_data, format="multipart")

    assert (response.status_code, response.json()) == (
        status.HTTP_201_CREATED,
        {
            "id": eq(lambda x: isinstance(x, int)),
            "file_name": "testfile.txt",
            "file_size": 12,
            "description": "",
            "created_at": eq(lambda x: bool(datetime.fromisoformat(x))),
            "url": eq(lambda x: x.startswith("http://testserver/media/") and x.endswith("testfile.txt")),
        },
    )
    assert UploadedFile.objects.count() == 1
    uploaded_file = UploadedFile.objects.first()
    assert uploaded_file.file_name == "testfile.txt"
    assert uploaded_file.description == ""
    assert uploaded_file.file_size == 12


@pytest.mark.django_db
def test_list_files(api_client, eq):
    UploadedFile.objects.create(file_name="file1.txt", file_size=1, storage_file_name="file1.txt")
    UploadedFile.objects.create(file_name="file2.txt", file_size=2, storage_file_name="file2.txt")

    response = api_client.get(V1_FILES_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": eq(lambda x: isinstance(x, int)),
            "file_name": "file1.txt",
            "file_size": 1,
            "description": "",
            "created_at": eq(lambda x: bool(datetime.fromisoformat(x))),
            "url": eq(lambda x: x.startswith("http://testserver/media/") and x.endswith("file1.txt")),
        },
        {
            "id": eq(lambda x: isinstance(x, int)),
            "file_name": "file2.txt",
            "file_size": 2,
            "description": "",
            "created_at": eq(lambda x: bool(datetime.fromisoformat(x))),
            "url": eq(lambda x: x.startswith("http://testserver/media/") and x.endswith("file2.txt")),
        },
    ]


@pytest.mark.django_db
def test_list_files_empty(api_client):
    response = api_client.get(V1_FILES_URL)
    assert (response.status_code, response.json()) == (status.HTTP_200_OK, [])
