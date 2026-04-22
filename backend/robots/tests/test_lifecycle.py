# ruff: noqa
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from django.utils.timezone import now
from asgiref.sync import sync_to_async
from robots.models import Robot, Telemetry, Alert
from robots.mqtt_handler import MQTTHandler
import json


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_full_robot_lifecycle():
    # 1. Setup mock Redis
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    mock_redis.llen.return_value = 0
    mock_redis.incr.return_value = 1

    with (
        patch("robots.mqtt_handler.redis.Redis", return_value=mock_redis),
        patch("robots.mqtt_handler.redis.ConnectionPool", return_value=MagicMock()),
    ):
        handler = MQTTHandler()

        # 2. Simulate MQTT message
        robot_id = "R-TEST-1"
        payload = {
            "robot_id": robot_id,
            "battery": 85.5,
            "status": "active",
            "timestamp": 1713715200.0,
        }

        await handler.on_message(
            client=None,
            topic=f"robots/{robot_id}/telemetry",
            payload=json.dumps(payload).encode(),
            qos=0,
            properties=None,
        )

        # 3. Flush to DB
        # Since Redis is mocked, lrange won't automatically return what was rpushed
        # We need to simulate the data that would be in the buffer.
        # on_message formats the timestamp as ISO-8601 string before pushing.
        from django.utils import timezone

        mock_redis.lrange.return_value = [
            json.dumps(
                {
                    "robot_id": robot_id,
                    "battery": 85.5,
                    "status": "active",
                    "timestamp": timezone.now().isoformat(),
                }
            ).encode()
        ]
        await handler.flush_to_db()

        # 4. Verify DB state
        robot = await sync_to_async(Robot.objects.get)(robot_id=robot_id)
        assert robot.status == "active"

        telemetry_exists = await sync_to_async(
            Telemetry.objects.filter(robot=robot, battery_lvl=85.5).exists
        )()
        assert telemetry_exists


@pytest.mark.django_db
def test_api_access(client):
    response = client.get("/api/robots/")
    assert response.status_code in [200, 401]  # Depends on auth config
