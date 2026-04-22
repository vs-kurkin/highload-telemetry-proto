# ruff: noqa
"""Temporary docstring."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from django.conf import settings


@pytest.mark.asyncio
@pytest.mark.django_db
class TestMQTTHandlerCoverage:
    async def test_connect_retry_logging(self, handler):
        mock_client = AsyncMock()
        # First connect fails, second fails, third succeeds
        mock_client.connect.side_effect = [OSError("Fail 1"), Exception("Fail 2"), None]
        mock_client.subscribe = AsyncMock()

        with patch("robots.mqtt_handler.MQTTClient", return_value=mock_client):
            with patch("asyncio.sleep", return_value=None):
                await handler.connect()
                assert mock_client.connect.call_count == 3
                assert mock_client.subscribe.called

    async def test_on_message_buffer_full(self, handler):
        # Mock llen to return more than MAX_BUFFER_SIZE
        handler.redis_client.llen = AsyncMock(return_value=settings.TELEMETRY_MAX_BUFFER_SIZE + 1)

        payload = json.dumps({"robot_id": "R1", "battery": 50.0, "status": "OK", "timestamp": 1234567890.0}).encode()

        await handler.on_message(None, "topic", payload, 0, None)
        # Should return early, rpush NOT called
        assert not handler.redis_client.rpush.called

    async def test_on_message_general_exception(self, handler):
        # Mock llen to raise exception
        handler.redis_client.llen = AsyncMock(side_effect=Exception("Redis Down"))

        payload = json.dumps({"robot_id": "R1", "battery": 50.0, "status": "OK", "timestamp": 1234567890.0}).encode()

        # This should hit the 'except Exception as e' block and log error
        await handler.on_message(None, "topic", payload, 0, None)

    async def test_handle_alert_exception(self, handler):
        # Mock redis.get to raise exception
        handler.redis_client.get = AsyncMock(side_effect=Exception("Redis Error"))

        # This should hit the 'except Exception as e' in handle_alert
        await handler.handle_alert("R1", 5.0)

    async def test_flush_buffer_loop_exception(self, handler):
        # Mock flush_to_db to raise exception, then KeyboardInterrupt to exit loop
        with patch.object(handler, "flush_to_db", side_effect=[Exception("Flush Fail"), KeyboardInterrupt()]):
            with patch("asyncio.sleep", return_value=None):
                try:
                    await handler.flush_buffer_loop()
                except KeyboardInterrupt:
                    pass

    async def test_prune_old_telemetry_exception(self, handler):
        # Mock connection cursor or something to raise exception
        with patch("django.db.connection.cursor", side_effect=Exception("DB Error")):
            # Call the underlying sync function directly to ensure coverage collection
            # because pytest-cov sometimes struggles with threads
            handler.prune_old_telemetry.func(handler)

    async def test_flush_to_db_parse_error(self, handler):
        # Mock lrange to return invalid JSON
        handler.redis_client.lrange = AsyncMock(return_value=[b"invalid-json"])
        handler.redis_client.set = AsyncMock(return_value=True)  # lock
        handler.redis_client.delete = AsyncMock()  # unlock

        await handler.flush_to_db()
        # Should log error and return
        assert not handler.redis_client.ltrim.called

    async def test_connect_with_shared_group(self, handler):
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.subscribe = AsyncMock()

        with (
            patch("robots.mqtt_handler.MQTTClient", return_value=mock_client),
            patch("django.conf.settings.MQTT_SHARED_GROUP", "testgroup"),
        ):
            await handler.connect()
            assert "$share/testgroup/" in mock_client.subscribe.call_args[0][0]

    async def test_flush_to_db_lock_acquired(self, handler):
        # Mock set to return False (lock held by someone else)
        handler.redis_client.set = AsyncMock(return_value=False)
        await handler.flush_to_db()
        # Should return early, lrange NOT called
        assert not handler.redis_client.lrange.called

    async def test_flush_to_db_empty_buffer(self, handler):
        # Lock acquired but no messages
        handler.redis_client.set = AsyncMock(return_value=True)
        handler.redis_client.lrange = AsyncMock(return_value=[])
        handler.redis_client.delete = AsyncMock()
        await handler.flush_to_db()
        assert handler.redis_client.delete.called

    async def test_bulk_save_telemetry_none(self, handler):
        await handler.bulk_save_telemetry([], {})

    async def test_flush_buffer_loop_stop_iteration(self, handler):
        # Use StopAsyncIteration to break the loop if possible, or just a custom exception
        class ExitLoop(BaseException):
            pass

        with patch.object(handler, "flush_to_db", side_effect=[Exception("Handled"), ExitLoop()]):
            with patch("asyncio.sleep", return_value=None):
                try:
                    await handler.flush_buffer_loop()
                except ExitLoop:
                    pass
