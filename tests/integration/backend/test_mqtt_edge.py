# ruff: noqa
"""Temporary docstring."""

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

    async def test_on_connect_various_codes(self):
        # RC 0 is success, others are errors
        self.handler.on_connect(None, None, 0, None)
        self.handler.on_connect(None, None, 5, None)

    async def test_on_message_payload_types(self):
        # Line 215: raw_data is not a dict
        msg = MagicMock()
        msg.payload = b'"just a string"'
        # Correct arguments: self, client, topic, payload, qos, properties
        await self.handler.on_message(None, "topic", msg.payload, 0, None)

        # Line 231-232: ValidationError (missing robot_id)
        msg.payload = b'{"battery": 50}'
        await self.handler.on_message(None, "topic", msg.payload, 0, None)

    async def test_on_message_redis_buffer_full(self):
        # Line 236: buffer >= settings.TELEMETRY_MAX_BUFFER_SIZE
        self.handler.redis_client.llen.return_value = 1000000
        msg = MagicMock()
        msg.payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'

        with patch("django.conf.settings.TELEMETRY_MAX_BUFFER_SIZE", 100):
            await self.handler.on_message(None, "topic", msg.payload, 0, None)
            assert not self.handler.redis_client.rpush.called

    async def test_on_message_rate_limit_hit(self):
        # Line 243: rate limit hit
        self.handler.redis_client.llen.return_value = 0
        self.handler.redis_client.set.return_value = False  # nx=True failed

        msg = MagicMock()
        msg.payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'

        with patch("os.getenv", return_value="1"):
            await self.handler.on_message(None, "topic", msg.payload, 0, None)
            assert not self.handler.redis_client.rpush.called

    async def test_on_message_exception(self):
        # Line 266: Generic Exception
        self.handler.redis_client.llen.side_effect = Exception("Redis explode")
        msg = MagicMock()
        msg.payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'
        await self.handler.on_message(None, "topic", msg.payload, 0, None)

    async def test_flush_to_db_batch_parse_error(self):
        # Line 345: Error parsing buffered message
        self.handler.redis_client.set.return_value = True  # lock acquired
        self.handler.redis_client.lrange.return_value = [b"invalid json"]
        await self.handler.flush_to_db()

    async def test_flush_to_db_critical_error(self):
        # Line 365: Critical error flushing to DB
        self.handler.redis_client.set.return_value = True
        self.handler.redis_client.lrange.return_value = [
            b'{"robot_id":"R1", "battery":50, "status":"OK", "timestamp":"2026-04-21T00:00:00"}'
        ]
        self.handler.redis_client.incr.return_value = 1

        with patch.object(self.handler, "bulk_save_telemetry", side_effect=Exception("DB Dead")):
            await self.handler.flush_to_db()

    async def test_prune_old_telemetry_exception(self):
        # Line 323: Error during lifecycle maintenance

        with patch(
            "robots.models.TelemetryDailyStats.objects.filter",
            side_effect=Exception("Maintenance fail"),
        ):
            await self.handler.prune_old_telemetry()

    async def test_flush_buffer_loop_error(self):
        # Line 283: Error in flush loop
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

    async def test_connect_retry_logic(self):
        # Line 165, 186-187: Retry logic
        with patch("robots.mqtt_handler.MQTTClient", return_value=AsyncMock()) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.connect.side_effect = [Exception("First fail"), None]
            mock_client.subscribe = AsyncMock()

            with patch("asyncio.sleep", return_value=None) as mock_sleep:
                await self.handler.connect()
                assert mock_sleep.call_count == 1
                assert mock_client.subscribe.called
