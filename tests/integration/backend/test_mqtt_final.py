# ruff: noqa
"""Final coverage for optimized MQTT Handler."""

import asyncio
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
        self.handler._lua_push = AsyncMock()

    async def test_on_message_success_metrics(self):
        self.handler._lua_push.return_value = b'OK'
        msg_payload = b'{"robot_id": "R1", "battery": 50, "timestamp": 1713715200.0}'
        
        with patch("prometheus_client.Counter.inc") as mock_inc:
            await self.handler.on_message(None, "topic", msg_payload, 0, None)
            assert mock_inc.called

    async def test_handle_alert_redis_error(self):
        self.handler.redis_client.set.side_effect = Exception("Redis down")
        await self.handler.handle_alert("R1", 10.0)

    async def test_flush_to_db_empty_batch(self):
        self.handler.redis_client.set.return_value = True
        self.handler.redis_client.lrange.return_value = []
        await self.handler.flush_to_db()

    async def test_flush_to_db_all_parse_errors(self):
        self.handler.redis_client.set.return_value = True
        self.handler.redis_client.lrange.return_value = [b"bad1", b"bad2"]
        await self.handler.flush_to_db()

    async def test_prune_old_telemetry_general_exception(self):
        with patch(
            "django.db.models.query.QuerySet.filter",
            side_effect=Exception("Query failed"),
        ):
            await self.handler.prune_old_telemetry()

    async def test_on_connect_error_log(self):
        # rc != 0
        self.handler.on_connect(None, {}, 1, None)

    async def test_on_message_no_schema_data(self):
        # Validation error (missing required field)
        msg_payload = b'{"status": "OK"}'
        await self.handler.on_message(None, "topic", msg_payload, 0, None)
        assert not self.handler._lua_push.called
