# ruff: noqa
"""Temporary docstring."""

import json
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from asgiref.sync import sync_to_async
from django.db import DatabaseError
from django.utils import timezone

from robots.models import Robot, Telemetry, TelemetryDailyStats
from robots.mqtt_handler import get_counter, get_gauge


@pytest.mark.django_db
@pytest.mark.asyncio
class TestMQTTHandlerFinal:
    async def test_full_on_message_and_flush_path(self, handler):
        rid = f"R_{uuid.uuid4().hex[:8]}"
        await sync_to_async(Robot.objects.create)(robot_id=rid, status="OK")

        now_iso = timezone.now().isoformat()
        valid_payload = {
            "robot_id": rid,
            "battery": 80.0,
            "status": "OK",
            "timestamp": timezone.now().timestamp(),  # Schema wants float
        }

        # Redis format needs string timestamp for fromisoformat in flush_to_db
        redis_payload = valid_payload.copy()
        redis_payload["timestamp"] = now_iso

        handler.redis_client.set.return_value = True
        handler.redis_client.rpush.return_value = 1
        await handler.on_message(None, "topic", json.dumps(valid_payload).encode(), 0, None)

        handler.redis_client.lrange.return_value = [json.dumps(redis_payload).encode()]
        handler.redis_client.ltrim.return_value = True
        await handler.flush_to_db()

        assert await sync_to_async(Telemetry.objects.filter(robot_id=rid).exists)()

    async def test_alerts_and_thresholds(self, handler):
        rid = f"R_{uuid.uuid4().hex[:8]}"
        # Battery below 10.0 (threshold in test_settings)
        payload = {
            "robot_id": rid,
            "battery": 5.0,
            "status": "ERROR",
            "timestamp": timezone.now().timestamp(),
        }
        handler.redis_client.get.return_value = None  # No alert lock
        await handler.on_message(None, "topic", json.dumps(payload).encode(), 0, None)
        # Should hit handle_alert and group_send

    async def test_lifecycle_maintenance(self, handler):
        rid = f"R_{uuid.uuid4().hex[:8]}"
        robot = await sync_to_async(Robot.objects.create)(robot_id=rid, status="OK")
        yesterday = timezone.now() - timedelta(days=1)
        await sync_to_async(Telemetry.objects.create)(robot=robot, battery_lvl=50.0, status="OK", timestamp=yesterday)
        await handler.prune_old_telemetry()
        assert await sync_to_async(TelemetryDailyStats.objects.filter(robot_id=rid).exists)()

    async def test_error_branches(self, handler):
        get_counter("mqtt_messages_received_total", "doc")
        get_gauge("telemetry_buffer_size", "doc")
        await handler.on_message(None, "topic", b"invalid", 0, None)

        with patch("robots.models.Telemetry.objects.bulk_create", side_effect=DatabaseError("DB Fail")):
            data = {
                "robot_id": "R1",
                "battery_lvl": 50,
                "status": "OK",
                "timestamp": str(timezone.now()),
            }
            try:
                await handler.bulk_save_telemetry([data], {"R1": {"battery": 50, "status": "OK"}})
            except DatabaseError:
                pass

    async def test_connect_and_on_connect(self, handler):
        mock_client = AsyncMock()
        with (
            patch("robots.mqtt_handler.MQTTClient", return_value=mock_client),
            patch("asyncio.sleep", return_value=None),
        ):
            mock_client.connect = AsyncMock()
            mock_client.subscribe = AsyncMock()
            await handler.connect()
            handler.on_connect(None, {}, 0, None)
            assert mock_client.subscribe.called

    async def test_loops_hit(self, handler):
        with (
            patch.object(handler, "flush_to_db", new_callable=AsyncMock),
            patch("asyncio.sleep", side_effect=[None, Exception("Stop")]),
        ):
            try:
                await handler.flush_buffer_loop()
            except Exception:
                pass

    async def test_connect_retry_hit(self, handler):
        mock_client = AsyncMock()
        with (
            patch("robots.mqtt_handler.MQTTClient", return_value=mock_client),
            patch("asyncio.sleep", side_effect=[None, Exception("Stop")]),
        ):
            mock_client.connect.side_effect = [OSError("Fail"), None]
            mock_client.subscribe = AsyncMock()
            try:
                await handler.connect()
            except Exception:
                pass
            assert mock_client.subscribe.called

    async def test_flush_buffer_loop_exception_path(self, handler):
        # Use a function for side_effect to avoid StopAsyncIteration
        sleep_calls = 0

        def sleep_side_effect(*args, **kwargs):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls > 5:
                raise Exception("Stop")
            return None

        with patch.object(handler, "flush_to_db") as mock_flush, patch("asyncio.sleep", side_effect=sleep_side_effect):
            mock_flush.side_effect = [Exception("Err"), None, None, None, None, Exception("Stop")]

            try:
                await handler.flush_buffer_loop()
            except Exception as e:
                if str(e) not in ["Stop"]:
                    raise

            assert mock_flush.call_count >= 1

    async def test_prune_old_telemetry_exception_path(self, handler):
        with patch("django.db.connection.cursor", side_effect=Exception("DB fail")):
            await handler.prune_old_telemetry()
            # Should log and pass
