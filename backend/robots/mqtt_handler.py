# ruff: noqa
"""Temporary docstring."""

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol, TypedDict, cast

import redis.asyncio as redis
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer  # type: ignore[import-untyped]
from django.conf import settings
from django.utils import timezone
from gmqtt import Client as MQTTClient  # type: ignore[import-untyped]
from prometheus_client import REGISTRY, Counter, Gauge
from pydantic import BaseModel, Field, ValidationError

from .constants import (
    ALERT_LOCK_PREFIX,
    ALERT_LOCK_VALUE,
    DEFAULT_QOS,
    DLQ_MAX_RETRIES,
    MQTT_RATE_LIMIT_PREFIX,
    MQTT_RATE_LIMIT_SECONDS,
    OPERATORS_GROUP_NAME,
    STATUS_OK,
    TELEMETRY_BUFFER_KEY,
    TELEMETRY_DLQ_KEY,
    TELEMETRY_TOPIC_FILTER,
)
from .models import Alert, Robot, Telemetry

if TYPE_CHECKING:
    from .models import Alert

logger = logging.getLogger(__name__)


class TelemetrySchema(BaseModel):
    """Validation schema for incoming robot telemetry data."""

    robot_id: str = Field(..., min_length=1)
    battery: float = Field(..., ge=0, le=100)
    status: str = Field(default=STATUS_OK)
    timestamp: float = Field(...)


class TelemetryEntry(TypedDict):
    """Data structure for buffering telemetry in Redis."""

    robot_id: str
    battery: float
    status: str
    timestamp: str


class RobotState(TypedDict):
    """Data structure for real-time robot state updates."""

    battery: float
    status: str


class TelemetryPersistData(TypedDict):
    """Data structure for persisting telemetry to the database."""

    robot_id: str
    battery_lvl: float
    status: str
    timestamp: str


class ChannelLayer(Protocol):
    """Protocol for Django Channels layer to support typing."""

    async def group_send(self, group: str, message: dict[str, object]) -> None: ...


def get_counter(name: str, documentation: str) -> Counter:
    if name in REGISTRY._names_to_collectors:
        return cast(Counter, REGISTRY._names_to_collectors[name])
    return Counter(name, documentation)


def get_gauge(name: str, documentation: str) -> Gauge:
    if name in REGISTRY._names_to_collectors:
        return cast(Gauge, REGISTRY._names_to_collectors[name])
    return Gauge(name, documentation)


# Prometheus Metrics
MQTT_MESSAGES_RECEIVED = get_counter("mqtt_messages_received_total", "Total MQTT messages received")
TELEMETRY_BUFFER_SIZE = get_gauge(
    "telemetry_buffer_size", "Current number of messages in Redis buffer"
)
DB_FLUSH_COUNT = get_counter("db_flush_total", "Total database flushes performed")
DB_PERSIST_ERROR = get_counter(
    "db_persist_errors_total", "Total errors during database persistence"
)


class MQTTClientProtocol(Protocol):
    def subscribe(self, topic: str, qos: int = 0) -> Awaitable[object]: ...
    def publish(
        self, topic: str, payload: bytes | str, qos: int = 0, retain: bool = False
    ) -> None: ...
    async def connect(self, host: str, port: int = 1883, keepalive: int = 60) -> None: ...
    @property
    def on_message(self) -> Callable[[object, str, bytes, int, object], Awaitable[None]]: ...
    @on_message.setter
    def on_message(
        self, val: Callable[[object, str, bytes, int, object], Awaitable[None]]
    ) -> None: ...
    @property
    def on_connect(self) -> Callable[[object, dict[str, int], int, object], None]: ...
    @on_connect.setter
    def on_connect(self, val: Callable[[object, dict[str, int], int, object], None]) -> None: ...


class MQTTHandler:
    """
    Orchestrates MQTT communication, Redis buffering, and database persistence.
    Handles high-load telemetry streams with rate-limiting and batch processing.
    """

    redis_client: "redis.Redis[bytes]"
    buffer_key: str
    dlq_key: str
    flush_interval: float
    channel_layer: ChannelLayer | None
    client: MQTTClientProtocol
    _redis_semaphore: asyncio.Semaphore | None = None

    def __init__(self) -> None:
        pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            max_connections=1000,
        )
        self.redis_client = redis.Redis(connection_pool=pool)
        self.buffer_key = TELEMETRY_BUFFER_KEY
        self.dlq_key = TELEMETRY_DLQ_KEY
        self.flush_interval = settings.TELEMETRY_FLUSH_INTERVAL
        self.channel_layer = cast(ChannelLayer | None, get_channel_layer())

    async def connect(self) -> None:
        """Establishes connection to MQTT broker and subscribes to telemetry topic."""
        self.client = MQTTClient("django-backend-consumer-" + os.getenv("HOSTNAME", "default"))
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect

        retry_count = 0
        while True:
            try:
                host, port = settings.MQTT_HOST, settings.MQTT_PORT
                logger.info(f"Connecting to MQTT at {host}:{port} (Attempt {retry_count + 1})")
                await self.client.connect(host, port)
                break
            except Exception as e:
                retry_count += 1
                wait = min(2**retry_count, 60)
                logger.error(f"MQTT Connection failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

        # Use Shared Subscription if configured to allow horizontal scaling
        topic = TELEMETRY_TOPIC_FILTER
        if settings.MQTT_SHARED_GROUP:
            topic = f"$share/{settings.MQTT_SHARED_GROUP}/{topic}"

        self.client.subscribe(topic, qos=DEFAULT_QOS)
        logger.info(f"Subscribed to {topic}")

    def on_connect(
        self, client: MQTTClient, flags: dict[str, int], rc: int, properties: object
    ) -> None:
        logger.info(f"Connected to MQTT Broker with result code {rc}")

    async def on_message(
        self, client: object, topic: str, payload: bytes, qos: int, properties: object
    ) -> None:
        if self._redis_semaphore is None:
            self._redis_semaphore = asyncio.Semaphore(100)

        async with self._redis_semaphore:
            try:
                # Step 0: Validation
                data = self._validate_payload(payload, topic)
                if not data:
                    return

                # Step 1: Circuit Breaker
                buffer_size = await self.redis_client.llen(self.buffer_key)
                if buffer_size >= settings.TELEMETRY_MAX_BUFFER_SIZE:
                    return

                # Step 2: Rate Limiting
                if await self._is_rate_limited(data.robot_id):
                    return

                # Step 3: Buffer and Stats
                await self._buffer_telemetry(data)

                # Step 4: Alerts
                if data.battery < settings.ALERT_BATTERY_THRESHOLD:
                    await self.handle_alert(data.robot_id, data.battery)

            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Invalid MQTT payload on {topic}: {e}")
            except Exception as e:
                logger.error(f"Error processing MQTT message: {e}")

    def _validate_payload(self, payload: bytes, topic: str) -> TelemetrySchema | None:
        raw_data = json.loads(payload.decode())
        if not isinstance(raw_data, dict):
            logger.warning(f"Invalid MQTT payload type on {topic}: {type(raw_data)}")
            return None

        return TelemetrySchema(
            robot_id=str(raw_data.get("robot_id", "")),
            battery=float(raw_data.get("battery", 0)),
            status=str(raw_data.get("status", STATUS_OK)),
            timestamp=float(raw_data.get("timestamp", timezone.now().timestamp())),
        )

    async def _is_rate_limited(self, robot_id: str) -> bool:
        rate_limit = int(os.getenv("MQTT_RATE_LIMIT_SECONDS", MQTT_RATE_LIMIT_SECONDS))
        if rate_limit > 0:
            limit_key = f"{MQTT_RATE_LIMIT_PREFIX}{robot_id}"
            if not await self.redis_client.set(limit_key, "1", ex=rate_limit, nx=True):
                return True
        return False

    async def _buffer_telemetry(self, data: TelemetrySchema) -> None:
        MQTT_MESSAGES_RECEIVED.inc()
        entry: TelemetryEntry = {
            "robot_id": data.robot_id,
            "battery": data.battery,
            "status": data.status,
            "timestamp": timezone.now().isoformat(),
        }
        await self.redis_client.rpush(self.buffer_key, json.dumps(entry))

    async def handle_alert(self, robot_id: str, battery: float) -> None:
        try:
            alert_lock_key = f"{ALERT_LOCK_PREFIX}{robot_id}"
            if not await self.redis_client.get(alert_lock_key):
                # Throttle alerts to avoid DB spam
                await self.redis_client.set(
                    alert_lock_key, ALERT_LOCK_VALUE, ex=settings.ALERT_THROTTLE_SECONDS
                )

                await self.create_db_alert(robot_id, f"Low battery: {battery}%")

                if self.channel_layer:
                    await self.channel_layer.group_send(
                        OPERATORS_GROUP_NAME,
                        {
                            "type": "alert_notification",
                            "data": {
                                "robot_id": robot_id,
                                "message": f"Low battery: {battery}%",
                                "battery": battery,
                            },
                        },
                    )
        except Exception as e:
            logger.error(f"Error handling alert for {robot_id}: {e}")

    @sync_to_async
    def create_db_alert(self, robot_id: str, message: str) -> Alert:
        robot, _ = Robot.objects.get_or_create(robot_id=robot_id)
        return Alert.objects.create(robot=robot, message=message)

    async def flush_buffer_loop(self) -> None:
        """Background loop for flushing Redis buffer and pruning old data."""
        prune_counter = 0
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_to_db()

                # Prune old data every 10 flush cycles to save DB IO
                prune_counter += 1
                if prune_counter >= 10:
                    await self.prune_old_telemetry()
                    prune_counter = 0
            except Exception as e:
                logger.error(f"Error in flush loop: {e}. Retrying in 1s...")
                await asyncio.sleep(1)

    @sync_to_async
    def prune_old_telemetry(self) -> None:
        """
        Aggregates data before pruning to maintain history.
        Uses a simpler, less locking-intensive pruning strategy.
        """
        from django.db import connection
        from django.db.models import Avg, Count, Max, Min
        from django.utils import timezone

        from .models import Telemetry, TelemetryDailyStats

        try:
            # 1. Aggregate yesterday's data
            yesterday = (timezone.now() - timedelta(days=1)).date()

            robot_ids = (
                Telemetry.objects.filter(timestamp__date=yesterday)
                .values_list("robot_id", flat=True)
                .distinct()
            )

            for rid in robot_ids:
                if not TelemetryDailyStats.objects.filter(robot_id=rid, date=yesterday).exists():
                    stats = Telemetry.objects.filter(
                        robot_id=rid, timestamp__date=yesterday
                    ).aggregate(
                        avg=Avg("battery_lvl"),
                        min=Min("battery_lvl"),
                        max=Max("battery_lvl"),
                        count=Count("id"),
                    )
                    if stats["count"] and stats["count"] > 0:
                        TelemetryDailyStats.objects.get_or_create(
                            robot_id=rid,
                            date=yesterday,
                            defaults={
                                "avg_battery": stats["avg"],
                                "min_battery": stats["min"],
                                "max_battery": stats["max"],
                                "message_count": stats["count"],
                            },
                        )

            # 2. Prune old records (Chunked Delete)
            total_deleted = 0
            with connection.cursor() as cursor:
                while True:
                    cursor.execute(
                        """
                        DELETE FROM robots_telemetry
                        WHERE id IN (
                            SELECT id FROM robots_telemetry
                            WHERE timestamp < %s
                            LIMIT 10000
                        )
                    """,
                        [yesterday],
                    )
                    deleted_count = cursor.rowcount
                    total_deleted += deleted_count
                    if deleted_count < 10000:
                        break

            if total_deleted > 0:
                logger.info(f"Pruned {total_deleted} old telemetry records")

        except Exception as e:
            logger.error(f"Error during lifecycle maintenance: {e}")

    async def flush_to_db(self) -> None:
        """
        Flushes telemetry from Redis buffer to PostgreSQL.
        Uses a lock to prevent race conditions when multiple instances are running.
        """
        lock_key = f"{self.buffer_key}_lock"
        if not await self.redis_client.set(lock_key, "1", ex=60, nx=True):
            return

        try:
            batch_size = settings.TELEMETRY_BATCH_SIZE
            msgs: list[bytes] = await self.redis_client.lrange(self.buffer_key, 0, batch_size - 1)

            if not msgs:
                return

            telemetry_objs: list[TelemetryPersistData] = []
            robots_to_update: dict[str, RobotState] = {}

            for m in msgs:
                try:
                    data = cast(TelemetryEntry, json.loads(m.decode()))
                    rid = data["robot_id"]
                    robots_to_update[rid] = {"battery": data["battery"], "status": data["status"]}

                    telemetry_objs.append(
                        {
                            "robot_id": rid,
                            "battery_lvl": data["battery"],
                            "status": data["status"],
                            "timestamp": data["timestamp"],
                        }
                    )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing buffered message: {e}")

            if not telemetry_objs:
                return

            try:
                await self.bulk_save_telemetry(telemetry_objs, robots_to_update)
                await self.redis_client.ltrim(self.buffer_key, len(msgs), -1)

                # Reset error counter on success
                await self.redis_client.delete(f"{self.buffer_key}_errors")

                DB_FLUSH_COUNT.inc()
                buffer_len = await self.redis_client.llen(self.buffer_key)
                TELEMETRY_BUFFER_SIZE.set(buffer_len)

                if self.channel_layer:
                    ws_message: dict[str, object] = {
                        "type": "telemetry_update",
                        "data": cast(dict[str, object], robots_to_update),
                    }
                    await self.channel_layer.group_send(OPERATORS_GROUP_NAME, ws_message)
                    logger.info(
                        f"BROADCAST: Sent update for {len(robots_to_update)} robots via WebSocket"
                    )
            except Exception as e:
                logger.error(f"Critical error flushing to DB: {e}")
                DB_PERSIST_ERROR.inc()

                error_key = f"{self.buffer_key}_errors"
                fails = await self.redis_client.incr(error_key)
                if fails >= DLQ_MAX_RETRIES:
                    logger.error(f"Batch failed {fails} times. Moving to DLQ.")
                    await self.redis_client.rpush(self.dlq_key, *msgs)
                    await self.redis_client.ltrim(self.buffer_key, len(msgs), -1)
                    await self.redis_client.delete(error_key)
        finally:
            await self.redis_client.delete(lock_key)

    @sync_to_async
    def bulk_save_telemetry(
        self, telemetry_data: list[TelemetryPersistData], robots_state: dict[str, RobotState]
    ) -> None:
        from django.db import transaction

        if not telemetry_data:
            return

        with transaction.atomic():
            robot_objs = [
                Robot(robot_id=rid, status=state["status"]) for rid, state in robots_state.items()
            ]
            Robot.objects.bulk_create(
                robot_objs,
                update_conflicts=True,
                update_fields=["status"],
                unique_fields=["robot_id"],
            )

            telemetry_to_create = [
                Telemetry(
                    robot_id=d["robot_id"],
                    battery_lvl=d["battery_lvl"],
                    status=d["status"],
                    timestamp=d["timestamp"],
                )
                for d in telemetry_data
            ]
            Telemetry.objects.bulk_create(telemetry_to_create)
