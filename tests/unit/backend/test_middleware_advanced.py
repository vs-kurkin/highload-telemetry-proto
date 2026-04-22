# ruff: noqa
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser, User
from robots.middleware import JwtAuthMiddleware, get_user


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_user_logic():
    user = await database_sync_to_async(User.objects.create_user)(username="u1")
    u = await get_user(user.id)
    assert u.username == "u1"
    u_anon = await get_user(9999)
    assert isinstance(u_anon, AnonymousUser)


@pytest.mark.asyncio
async def test_middleware_query_token_success():
    inner = AsyncMock()
    mw = JwtAuthMiddleware(inner)

    with (
        patch("robots.middleware.AccessToken") as mock_token,
        patch("robots.middleware.get_user", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_token.return_value = {"user_id": 1}
        mock_get_user.return_value = MagicMock()

        scope = {"query_string": b"token=secret"}
        await mw(scope, None, None)

        assert scope["user"] == mock_get_user.return_value
        assert inner.called


@pytest.mark.asyncio
async def test_middleware_cookie_token_success():
    inner = AsyncMock()
    mw = JwtAuthMiddleware(inner)

    with (
        patch("robots.middleware.AccessToken") as mock_token,
        patch("robots.middleware.get_user", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_token.return_value = {"user_id": 1}
        mock_get_user.return_value = MagicMock()

        # Binary headers as they come in Channels
        scope = {"headers": [(b"cookie", b"access_token=cookie-secret")]}
        await mw(scope, None, None)

        assert scope["user"] == mock_get_user.return_value


@pytest.mark.asyncio
async def test_middleware_token_invalid_error():
    inner = AsyncMock()
    mw = JwtAuthMiddleware(inner)

    with patch("robots.middleware.AccessToken", side_effect=Exception("Invalid")):
        scope = {"query_string": b"token=bad"}
        await mw(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)


@pytest.mark.asyncio
async def test_middleware_critical_error():
    inner = AsyncMock()
    mw = JwtAuthMiddleware(inner)

    # Trigger Exception in parse_qs or decode
    scope = {"query_string": None}  # None.decode() will fail
    await mw(scope, None, None)
    assert isinstance(scope["user"], AnonymousUser)
