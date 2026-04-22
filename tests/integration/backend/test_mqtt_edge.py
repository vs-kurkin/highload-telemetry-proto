# ruff: noqa
"""Edge cases for optimized MQTT Handler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from robots.mqtt_handler import MQTTHandler


@pytest.mark.asyncio
@pytest.mark.django_db
class TestMQTTHandlerEdgeCases:
    def setup_method(self):
        self.handler = MQTTHandler()
        self.handler.client = MagicMock()
        self.handler.redis_client = AsyncMock()
        self.handler._lua_push = AsyncMock()

    async def test_on_connect_various_codes(self):
        # RC 0 is success, others are errors
        self.handler.on_connect(None, {}, 0, None)
        self.handler.on_connect(None, {}, 5, None)

    async def test_on_message_payload_types(self):
        # raw_data is not a dict
        msg_payload = b'"just a string"'
        await self.handler.on_message(None, "topic", msg_payload, 0, None)
        assert not self.handler._lua_push.called

    async def test_on_message_redis_buffer_full(self):
        # Lua script returns BUFFER_FULL
        self.handler._lua_push.return_value = b'BUFFER_FULL'
        msg_payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'

        await self.handler.on_message(None, "topic", msg_payload, 0, None)
        assert self.handler._lua_push.called

    async def test_on_message_rate_limit_hit(self):
        # Lua script returns RATE_LIMITED
        self.handler._lua_push.return_value = b'RATE_LIMITED'
        msg_payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'

        await self.handler.on_message(None, "topic", msg_payload, 0, None)
        assert self.handler._lua_push.called

    async def test_on_message_exception(self):
        # Generic Exception during orjson.loads or pydantic validation
        msg_payload = b'{"robot_id": "R1", "battery": "not a float"}'
        await self.handler.on_message(None, "topic", msg_payload, 0, None)
        assert not self.handler._lua_push.called

    async def test_flush_to_db_batch_parse_error(self):
        self.handler.redis_client.set.return_value = True  # lock acquired
        self.handler.redis_client.lrange.return_value = [b"invalid json"]
        await self.handler.flush_to_db()

    async def test_flush_to_db_critical_error(self):
        self.handler.redis_client.set.return_value = True
        self.handler.redis_client.lrange.return_value = [
            b'{"robot_id":"R1", "battery":50, "status":"OK", "timestamp":"2026-04-21T00:00:00"}'
        ]

        with patch.object(
            self.handler, "bulk_save_telemetry", side_effect=Exception("DB Dead")
        ):
            await self.handler.flush_to_db()
            # Should push to DLQ
            assert self.handler.redis_client.rpush.called

    async def test_prune_old_telemetry_exception(self):
        with patch(
            "django.db.models.query.QuerySet.exclude",
            side_effect=Exception("Maintenance fail"),
        ):
            await self.handler.prune_old_telemetry()

    async def test_flush_buffer_loop_error(self):
        with patch.object(
            self.handler,
            "flush_to_db",
            side_effect=[Exception("Loop fail"), asyncio.CancelledError()],
        ):
            with patch("asyncio.sleep", return_value=None):
                try:
                    await self.handler.flush_buffer_loop()
                except asyncio.CancelledError:
                    pass
