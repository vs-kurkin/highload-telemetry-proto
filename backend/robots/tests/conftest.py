# ruff: noqa
"""Doc."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken

from robots.mqtt_handler import MQTTHandler


@pytest.fixture
def mock_redis():
    """Shared Redis client mock with full support for current MQTTHandler logic."""
    client = AsyncMock()
    client.set.return_value = True
    client.get.return_value = None
    client.llen.return_value = 0
    client.lrange.return_value = []
    client.ltrim.return_value = True
    client.delete.return_value = True
    client.rpush.return_value = 1

    # Mock pipeline if needed (though current handler uses direct calls mostly)
    pipeline = AsyncMock()
    client.pipeline.return_value = pipeline
    pipeline.execute.return_value = []

    return client


@pytest.fixture
def handler(mock_redis):
    """Shared MQTTHandler fixture with mocked Redis and Channels."""
    with (
        patch("robots.mqtt_handler.redis.Redis", return_value=mock_redis),
        patch("robots.mqtt_handler.redis.ConnectionPool", return_value=MagicMock()),
        patch("robots.mqtt_handler.get_channel_layer") as mock_get_channel_layer,
        patch.dict(os.environ, {"MQTT_RATE_LIMIT_SECONDS": "5", "HOSTNAME": "worker-1"}),
    ):
        mock_channel_layer = AsyncMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        h = MQTTHandler()
        h.redis_client = mock_redis
        h.channel_layer = mock_channel_layer
        return h


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient  # type: ignore[import-untyped]

    return APIClient()


@pytest.fixture
def test_user(db):
    """Shared test user fixture."""
    return User.objects.create_user(username="test_worker", password="password123")


@pytest.fixture
def api_token(test_user):
    """JWT token for API and WebSocket auth."""
    return str(AccessToken.for_user(test_user))


@pytest.fixture
async def authenticated_ws_communicator(transactional_db, api_token):
    """Helper to create authenticated WebSocket communicator."""
    from channels.testing import WebsocketCommunicator  # type: ignore[import-untyped]

    from telemetry_core.asgi import application

    communicator = WebsocketCommunicator(application, f"/ws/telemetry/?token={api_token}")
    connected, _ = await communicator.connect()
    assert connected
    yield communicator
    await communicator.disconnect()
