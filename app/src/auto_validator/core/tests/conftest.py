from collections.abc import Generator

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


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


@pytest.fixture
def api_client(auth_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token.key}")
    return client


@pytest.fixture
def eq():
    class EqualityMock:
        def __init__(self, func):
            self.func = func

        def __eq__(self, other):
            return self.func(other)

    return EqualityMock
