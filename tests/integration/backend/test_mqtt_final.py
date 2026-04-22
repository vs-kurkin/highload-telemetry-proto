# ruff: noqa
"""Temporary docstring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from robots.mqtt_handler import MQTTHandler


@pytest.mark.asyncio
@pytest.mark.django_db
class TestMQTTHandlerFinalCoverage:
    def setup_method(self):
        self.handler = MQTTHandler()
        self.handler.client = MagicMock()
        self.handler.redis_client = AsyncMock()

    async def test_connect_exception_handling(self):
        # Line 165-170: Exception during connect
        with patch("robots.mqtt_handler.MQTTClient", return_value=AsyncMock()) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.subscribe = AsyncMock()
            # Fail once, then succeed to exit loop
            mock_client.connect.side_effect = [Exception("Conn Error"), None]
            with patch("asyncio.sleep", return_value=None):
                await self.handler.connect()
                assert mock_client.connect.call_count == 2
                assert mock_client.subscribe.called

    async def test_on_message_json_decode_error(self):
        # Line 215/264: json.loads failure
        msg = MagicMock()
        msg.payload = b"not-json"
        await self.handler.on_message(None, "topic", msg.payload, 0, None)

    async def test_on_message_redis_rpush_error(self):
        # Line 257-258/266: Redis rpush failure
        self.handler.redis_client.llen.return_value = 0
        self.handler.redis_client.rpush.side_effect = Exception("Redis full")
        msg = MagicMock()
        msg.payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'
        await self.handler.on_message(None, "topic", msg.payload, 0, None)

    async def test_flush_to_db_redis_lrange_error(self):
        # Line 281-282/402: Redis lrange failure
        self.handler.redis_client.set.return_value = True  # lock ok
        self.handler.redis_client.lrange.side_effect = Exception("Lrange fail")
        # In the current implementation, lrange failure in flush_to_db is NOT caught internally
        with pytest.raises(Exception, match="Lrange fail"):
            await self.handler.flush_to_db()

    async def test_flush_to_db_parse_error_in_loop(self):
        # Line 345/354: json.loads failure inside flush loop
        self.handler.redis_client.set.return_value = True
        self.handler.redis_client.lrange.return_value = [
            b"invalid",
            (b'{"robot_id":"R1", "battery":50, "status":"OK", "timestamp":"2026-04-21T00:00:00+00:00"}'),
        ]
        await self.handler.flush_to_db()

    async def test_flush_to_db_bulk_save_error(self):
        # Line 358/365: bulk_save_telemetry failure
        self.handler.redis_client.set.return_value = True
        self.handler.redis_client.lrange.return_value = [
            b'{"robot_id":"R1", "battery":50, "status":"OK", "timestamp":"2026-04-21T00:00:00"}'
        ]
        self.handler.redis_client.incr.return_value = 1
        with patch.object(self.handler, "bulk_save_telemetry", side_effect=Exception("DB Dead")):
            await self.handler.flush_to_db()

    async def test_prune_old_telemetry_general_exception(self):
        # Line 417 (in some versions) or general catch 323
        with patch("robots.models.Telemetry.objects.filter", side_effect=Exception("Query failed")):
            await self.handler.prune_old_telemetry()

    async def test_on_connect_error_log(self):
        # rc != 0
        self.handler.on_connect(None, None, 1, None)
