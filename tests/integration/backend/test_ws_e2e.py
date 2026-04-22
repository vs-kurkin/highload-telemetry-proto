# ruff: noqa
"""Temporary docstring."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from robots.consumers import TelemetryConsumer


@pytest.mark.asyncio
@pytest.mark.django_db
class TestWebSocketSimplified:
    async def test_consumer_accepts_authenticated(self, api_token):
        consumer = TelemetryConsumer()
        # Mock scope and methods
        consumer.scope = {"user": MagicMock()}
        consumer.scope["user"].is_authenticated = True
        consumer.scope["user"].is_anonymous = False
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test_channel"
        consumer.accept = AsyncMock()
        consumer.base_send = AsyncMock()

        await consumer.connect()
        assert consumer.accept.called

    async def test_consumer_rejects_anonymous(self):
        consumer = TelemetryConsumer()
        consumer.scope = {"user": MagicMock()}
        consumer.scope["user"].is_anonymous = True
        consumer.close = AsyncMock()
        consumer.base_send = AsyncMock()

        await consumer.connect()
        assert consumer.close.called
