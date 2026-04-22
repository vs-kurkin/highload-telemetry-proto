# ruff: noqa
import pytest
from unittest.mock import MagicMock
from robots.authentication import CookieJWTAuthentication


def test_cookie_jwt_auth_no_header_no_cookie():
    auth = CookieJWTAuthentication()
    request = MagicMock()
    request.COOKIES = {}
    request.META = {}  # No HTTP_AUTHORIZATION

    # This should hit 'if header is not None' which will be False
    result = auth.authenticate(request)
    assert result is None


def test_cookie_jwt_auth_with_cookie_success():
    auth = CookieJWTAuthentication()
    request = MagicMock()
    request.COOKIES = {"access_token": "fake-token"}

    mock_user = MagicMock()
    mock_token = MagicMock()

    auth.get_validated_token = MagicMock(return_value=mock_token)
    auth.get_user = MagicMock(return_value=mock_user)

    result = auth.authenticate(request)
    assert result is not None
    assert result[0] == mock_user
    assert result[1] == mock_token


def test_cookie_jwt_auth_exception_handling():
    auth = CookieJWTAuthentication()
    request = MagicMock()
    request.COOKIES = {"access_token": "bad-token"}
    auth.get_validated_token = MagicMock(side_effect=Exception("Auth Fail"))

    result = auth.authenticate(request)
    assert result is None
