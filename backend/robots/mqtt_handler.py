# ruff: noqa
"""
Optimized MQTT Handler for Highload Telemetry Service.
Features: Lua scripting, orjson, strict typing, in-memory caching, and chunked DB operations.
"""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable, Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol, TypedDict, cast, Final, Literal, Any

import orjson
import redis.asyncio as redis
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer # type: ignore
from django.conf import settings
from django.utils import timezone
from gmqtt import Client as MQTTClient # type: ignore
from prometheus_client import REGISTRY, Counter, Gauge
from pydantic import BaseModel, Field

from .constants import (
    ALERT_LOCK_PREFIX,
    ALERT_LOCK_VALUE,
    DEFAULT_QOS,
    MQTT_RATE_LIMIT_PREFIX,
    MQTT_RATE_LIMIT_SECONDS,
    OPERATORS_GROUP_NAME,
    STATUS_OK,
    TELEMETRY_BUFFER_KEY,
    TELEMETRY_DLQ_KEY,
    TELEMETRY_TOPIC_FILTER,
)
from .models import Alert, Robot, Telemetry

logger = logging.getLogger(__name__)

LuaResponse = Literal[b'OK', b'BUFFER_FULL', b'RATE_LIMITED']

LUA_PUSH_TELEMETRY: Final[str] = """
local buffer_key = KEYS[1]
local limit_key = KEYS[2]
local max_buffer = tonumber(ARGV[1])
local rate_limit_expiry = tonumber(ARGV[2])
local payload = ARGV[3]

if redis.call('LLEN', buffer_key) >= max_buffer then
    return 'BUFFER_FULL'
end

if rate_limit_expiry > 0 then
    if not redis.call('SET', limit_key, '1', 'EX', rate_limit_expiry, 'NX') then
        return 'RATE_LIMITED'
    end
end

redis.call('RPUSH', buffer_key, payload)
return 'OK'
"""

class TelemetrySchema(BaseModel):
    robot_id: str = Field(..., min_length=1)
    battery: float = Field(..., ge=0, le=100)
    status: str = Field(default=STATUS_OK)
    timestamp: float = Field(...)

class TelemetryEntry(TypedDict):
    robot_id: str
    battery: float
    status: str
    timestamp: str

class RobotState(TypedDict):
    battery: float
    status: str

class TelemetryPersistData(TypedDict):
    robot_id: str
    battery_lvl: float
    status: str
    timestamp: str

class ChannelLayer(Protocol):
    async def group_send(self, group: str, message: dict[str, object]) -> None: ...

class MQTTClientProtocol(Protocol):
    def subscribe(self, topic: str, qos: int = 0) -> Awaitable[object]: ...
    async def connect(self, host: str, port: int = 1883, keepalive: int = 60) -> None: ...
    @property
    def on_message(self) -> Callable[[object, str, bytes, int, object], Awaitable[None]]: ...
    @on_message.setter
    def on_message(self, val: Callable[[object, str, bytes, int, object], Awaitable[None]]) -> None: ...
    @property
    def on_connect(self) -> Callable[[object, dict[str, int], int, object], None]: ...
    @on_connect.setter
    def on_connect(self, val: Callable[[object, dict[str, int], int, object], None]) -> None: ...

MQTT_MESSAGES_RECEIVED: Final[Counter] = Counter("mqtt_messages_received_total", "Total MQTT messages received")
TELEMETRY_BUFFER_SIZE: Final[Gauge] = Gauge("telemetry_buffer_size", "Current number of messages in Redis buffer")
DB_FLUSH_COUNT: Final[Counter] = Counter("db_flush_total", "Total database flushes performed")
DB_PERSIST_ERROR: Final[Counter] = Counter("db_persist_errors_total", "Total errors during database persistence")

class MQTTHandler:
    redis_client: redis.Redis
    _lua_push: Any
    buffer_key: str
    dlq_key: str
    flush_interval: float
    channel_layer: ChannelLayer | None
    client: MQTTClientProtocol
    _redis_semaphore: asyncio.Semaphore
    _robot_cache: set[str]

    def __init__(self) -> None:
        pool: redis.ConnectionPool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            max_connections=1000,
        )
        self.redis_client = redis.Redis(connection_pool=pool)
        self.buffer_key = TELEMETRY_BUFFER_KEY
        self.dlq_key = TELEMETRY_DLQ_KEY
        self.flush_interval = settings.TELEMETRY_FLUSH_INTERVAL
        self.channel_layer = cast(ChannelLayer | None, get_channel_layer())
        self._lua_push = self.redis_client.register_script(LUA_PUSH_TELEMETRY)
        self._redis_semaphore = asyncio.Semaphore(500)
        self._robot_cache = set()

    async def connect(self) -> None:
        self.client = MQTTClient("django-backend-consumer-" + os.getenv("HOSTNAME", "default"))
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect

        retry_count: int = 0
        while True:
            try:
                await self.client.connect(settings.MQTT_HOST, settings.MQTT_PORT)
                break
            except Exception:
                retry_count += 1
                await asyncio.sleep(min(2**retry_count, 60))

        topic: str = TELEMETRY_TOPIC_FILTER
        if settings.MQTT_SHARED_GROUP:
            topic = f"$share/{settings.MQTT_SHARED_GROUP}/{topic}"
        await self.client.subscribe(topic, qos=DEFAULT_QOS)

    def on_connect(self, client: object, flags: dict[str, int], rc: int, properties: object) -> None:
        logger.info(f"Connected to MQTT Broker (rc={rc})")

    async def on_message(self, client: object, topic: str, payload: bytes, qos: int, properties: object) -> None:
        async with self._redis_semaphore:
            try:
                raw_data: dict[str, Any] = orjson.loads(payload)
                data: TelemetrySchema = TelemetrySchema(**raw_data)
                
                limit_key: str = f"{MQTT_RATE_LIMIT_PREFIX}{data.robot_id}"
                rate_limit: int = int(os.getenv("MQTT_RATE_LIMIT_SECONDS", MQTT_RATE_LIMIT_SECONDS))
                
                entry: TelemetryEntry = {
                    "robot_id": data.robot_id,
                    "battery": data.battery,
                    "status": data.status,
                    "timestamp": timezone.now().isoformat(),
                }
                
                result: LuaResponse = await self._lua_push(
                    keys=[self.buffer_key, limit_key],
                    args=[settings.TELEMETRY_MAX_BUFFER_SIZE, rate_limit, orjson.dumps(entry)]
                )
                
                if result == b'OK':
                    MQTT_MESSAGES_RECEIVED.inc()
                    if data.battery < settings.ALERT_BATTERY_THRESHOLD:
                        await self.handle_alert(data.robot_id, data.battery)
            except Exception:
                pass

    async def handle_alert(self, robot_id: str, battery: float) -> None:
        try:
            alert_lock_key: str = f"{ALERT_LOCK_PREFIX}{robot_id}"
            if await self.redis_client.set(alert_lock_key, ALERT_LOCK_VALUE, ex=settings.ALERT_THROTTLE_SECONDS, nx=True):
                if robot_id not in self._robot_cache:
                    await self._ensure_robot_exists(robot_id)
                    self._robot_cache.add(robot_id)
                
                await self.save_alert(robot_id, f"Low battery: {battery}%")
                
                if self.channel_layer:
                    await self.channel_layer.group_send(
                        OPERATORS_GROUP_NAME,
                        {
                            "type": "alert_notification",
                            "data": {"robot_id": robot_id, "message": f"Low battery: {battery}%", "battery": battery},
                        },
                    )
        except Exception as e:
            logger.error(f"Alert error: {e}")

    @sync_to_async
    def _ensure_robot_exists(self, robot_id: str) -> None:
        Robot.objects.get_or_create(robot_id=robot_id)

    @sync_to_async
    def save_alert(self, robot_id: str, message: str) -> None:
        Alert.objects.create(robot_id=robot_id, message=message)

    async def flush_buffer_loop(self) -> None:
        prune_counter: int = 0
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_to_db()
                
                prune_counter += 1
                if prune_counter >= 300: # ~30 seconds if interval is 0.1s
                    await self.prune_old_telemetry()
                    prune_counter = 0
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
                await asyncio.sleep(1)

    @sync_to_async
    def prune_old_telemetry(self) -> None:
        from django.db import connection, transaction
        from django.db.models import Avg, Count, Max, Min
        from django.utils import timezone
        from .models import Telemetry, TelemetryDailyStats

        try:
            yesterday = (timezone.now() - timedelta(days=1)).date()
            with transaction.atomic():
                robots_needing_stats = Telemetry.objects.filter(
                    timestamp__date=yesterday
                ).exclude(
                    robot__daily_stats__date=yesterday
                ).values_list('robot_id', flat=True).distinct()

                for rid in robots_needing_stats:
                    stats = Telemetry.objects.filter(
                        robot_id=rid, timestamp__date=yesterday
                    ).aggregate(
                        avg=Avg("battery_lvl"),
                        min=Min("battery_lvl"),
                        max=Max("battery_lvl"),
                        count=Count("id"),
                    )
                    if stats["count"]:
                        TelemetryDailyStats.objects.get_or_create(
                            robot_id=rid,
                            date=yesterday,
                            defaults={
                                "avg_battery": stats["avg"] or 0,
                                "min_battery": stats["min"] or 0,
                                "max_battery": stats["max"] or 0,
                                "message_count": stats["count"],
                            },
                        )

            with connection.cursor() as cursor:
                total_deleted = 0
                while True:
                    cursor.execute(
                        "DELETE FROM robots_telemetry WHERE id IN (SELECT id FROM robots_telemetry WHERE timestamp < %s LIMIT 10000)",
                        [yesterday]
                    )
                    deleted = cursor.rowcount
                    total_deleted += deleted
                    if deleted < 10000: break
                if total_deleted > 0:
                    logger.info(f"Pruned {total_deleted} telemetry records.")
        except Exception as e:
            logger.error(f"Prune error: {e}")

    async def flush_to_db(self) -> None:
        lock_key: str = f"{self.buffer_key}_lock"
        if not await self.redis_client.set(lock_key, "1", ex=60, nx=True):
            return

        try:
            batch_size: int = settings.TELEMETRY_BATCH_SIZE
            msgs: list[bytes] = await self.redis_client.lrange(self.buffer_key, 0, batch_size - 1)
            if not msgs: return

            telemetry_objs: list[TelemetryPersistData] = []
            robots_to_update: dict[str, RobotState] = {}

            for m in msgs:
                try:
                    data: TelemetryEntry = orjson.loads(m)
                    rid: str = data["robot_id"]
                    robots_to_update[rid] = {"battery": data["battery"], "status": data["status"]}
                    telemetry_objs.append({
                        "robot_id": rid, "battery_lvl": data["battery"],
                        "status": data["status"], "timestamp": data["timestamp"],
                    })
                except Exception: continue

            if telemetry_objs:
                try:
                    await self.bulk_save_telemetry(telemetry_objs, robots_to_update)
                    await self.redis_client.ltrim(self.buffer_key, len(msgs), -1)
                    DB_FLUSH_COUNT.inc()
                    
                    if self.channel_layer:
                        await self.channel_layer.group_send(
                            OPERATORS_GROUP_NAME, 
                            {"type": "telemetry_update", "data": cast(dict[str, object], robots_to_update)}
                        )
                except Exception as e:
                    logger.error(f"DB Error: {e}")
                    DB_PERSIST_ERROR.inc()
                    await self.redis_client.rpush(self.dlq_key, *msgs)
                    await self.redis_client.ltrim(self.buffer_key, len(msgs), -1)
        finally:
            await self.redis_client.delete(lock_key)

    @sync_to_async
    def bulk_save_telemetry(
        self, 
        telemetry_data: Sequence[TelemetryPersistData], 
        robots_state: dict[str, RobotState]
    ) -> None:
        from django.db import transaction
        with transaction.atomic():
            robot_objs: list[Robot] = [
                Robot(robot_id=rid, status=state["status"]) 
                for rid, state in robots_state.items()
            ]
            Robot.objects.bulk_create(
                robot_objs, update_conflicts=True, update_fields=["status"], unique_fields=["robot_id"]
            )
            
            telemetry_to_create: list[Telemetry] = [
                Telemetry(
                    robot_id=d["robot_id"], 
                    battery_lvl=d["battery_lvl"], 
                    status=d["status"], 
                    timestamp=d["timestamp"]
                )
                for d in telemetry_data
            ]
            Telemetry.objects.bulk_create(telemetry_to_create)
