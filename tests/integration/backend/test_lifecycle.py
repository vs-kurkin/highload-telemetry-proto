# ruff: noqa
"""Temporary docstring."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from asgiref.sync import sync_to_async
from django.utils import timezone

from robots.models import Robot, Telemetry, TelemetryDailyStats
from robots.mqtt_handler import MQTTHandler


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.llen.return_value = 0
    mock.set.return_value = True
    mock.get.return_value = None
    mock.rpush.return_value = 1
    mock.lrange.return_value = []
    return mock


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_daily_aggregation(mock_redis):
    handler = MQTTHandler()
    handler.redis_client = mock_redis

    # Use sync_to_async for all DB operations
    robot_id = "R-LIFE-1"
    robot, _ = await sync_to_async(Robot.objects.get_or_create)(robot_id=robot_id)
    yesterday = timezone.now() - timedelta(days=1)

    await sync_to_async(Telemetry.objects.create)(robot=robot, battery_lvl=40.0, status="OK", timestamp=yesterday)
    await sync_to_async(Telemetry.objects.create)(robot=robot, battery_lvl=60.0, status="OK", timestamp=yesterday)

    await handler.prune_old_telemetry()

    stats = await sync_to_async(TelemetryDailyStats.objects.get)(robot_id=robot_id, date=yesterday.date())
    assert stats.avg_battery == 50.0
    assert stats.message_count == 2
