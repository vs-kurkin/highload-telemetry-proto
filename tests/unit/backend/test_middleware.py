# ruff: noqa
"""Temporary docstring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser

from robots.middleware import JwtAuthMiddleware


@pytest.mark.asyncio
@pytest.mark.django_db
class TestJwtAuthMiddlewareExtended:
    async def test_valid_token(self):
        inner = AsyncMock()
        middleware = JwtAuthMiddleware(inner)
        user = MagicMock()
        user.is_authenticated = True

        scope = {"query_string": b"token=valid_token"}

        # Mock AccessToken and get_user
        with patch("robots.middleware.AccessToken", return_value={"user_id": 1}):
            with patch("robots.middleware.get_user", return_value=user):
                await middleware(scope, None, None)
                assert scope["user"] == user
                inner.assert_called_once()

    async def test_no_token(self):
        inner = AsyncMock()
        middleware = JwtAuthMiddleware(inner)
        scope = {"query_string": b""}

        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)
        inner.assert_called_once()

    async def test_invalid_token_format(self):
        inner = AsyncMock()
        middleware = JwtAuthMiddleware(inner)
        scope = {"query_string": b"notatoken=123"}

        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)
        inner.assert_called_once()

    async def test_exception_in_token_parsing(self):
        inner = AsyncMock()
        middleware = JwtAuthMiddleware(inner)
        scope = {"query_string": b"token=invalid"}

        with patch("robots.middleware.AccessToken", side_effect=Exception("Invalid token")):
            await middleware(scope, None, None)
            assert isinstance(scope["user"], AnonymousUser)
            inner.assert_called_once()

    async def test_get_user_helper(self):
        from robots.middleware import get_user

        user = MagicMock()
        with patch("robots.middleware.User.objects.get", return_value=user):
            result = await get_user(1)
            assert result == user

        # Fix DoesNotExist mock
        from django.contrib.auth.models import User

        with patch("robots.middleware.User.objects.get", side_effect=User.DoesNotExist):
            result = await get_user(2)
            assert isinstance(result, AnonymousUser)

    async def test_missing_query_string_in_scope(self):
        inner = AsyncMock()
        middleware = JwtAuthMiddleware(inner)
        scope = {}  # No query_string

        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)
        inner.assert_called_once()
