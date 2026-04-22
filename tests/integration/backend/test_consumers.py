# ruff: noqa
"""Temporary docstring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from robots.consumers import TelemetryConsumer
from robots.routing import websocket_urlpatterns


@pytest.mark.asyncio
class TestTelemetryConsumerFinal:
    async def test_connect_and_disconnect_direct(self):
        consumer = TelemetryConsumer()
        consumer.scope = {"user": MagicMock()}
        consumer.scope["user"].is_authenticated = True
        consumer.scope["user"].is_anonymous = False
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test_channel"
        consumer.base_send = AsyncMock()

        with patch.object(TelemetryConsumer, "accept", new_callable=AsyncMock):
            await consumer.connect()

        assert consumer.group_name == "operators"
        await consumer.disconnect(1000)
        assert consumer.channel_layer.group_discard.called

    async def test_connect_unauthenticated_direct(self):
        consumer = TelemetryConsumer()
        consumer.scope = {"user": MagicMock()}
        consumer.scope["user"].is_anonymous = True
        consumer.close = AsyncMock()
        consumer.base_send = AsyncMock()

        await consumer.connect()
        assert consumer.close.called

    async def test_receive_does_nothing(self):
        # Coverage for the 'pass' in receive
        consumer = TelemetryConsumer()
        await consumer.receive("some text")

    async def test_broadcast_methods(self):
        consumer = TelemetryConsumer()
        consumer.send = AsyncMock()
        consumer.subscribed_robots.add("temp")

        await consumer.telemetry_update({"data": {"temp": 25}})
        await consumer.alert_notification({"data": {"msg": "fire"}})
        assert consumer.send.call_count == 2


def test_routing_exists():
    # Simply access the routing to cover the file
    assert len(websocket_urlpatterns) > 0
