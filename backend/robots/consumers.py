# ruff: noqa
"""Temporary docstring."""

import json
from typing import TYPE_CHECKING

from channels.generic.websocket import AsyncWebsocketConsumer  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User

from .constants import OPERATORS_GROUP_NAME


class TelemetryConsumer(AsyncWebsocketConsumer):  # type: ignore[misc]
    group_name: str
    subscribed_robots: set[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_robots = set()

    async def connect(self) -> None:
        # Authentication check
        user: User | AnonymousUser = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        self.group_name = OPERATORS_GROUP_NAME
        self.subscribed_robots = set()

        # Join the "operators" group for real-time updates
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        # Leave group on disconnect
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
            action = data.get("action")
            if action == "subscribe":
                robot_ids = data.get("robot_ids", [])
                if isinstance(robot_ids, list):
                    self.subscribed_robots.update(robot_ids)
            elif action == "unsubscribe":
                robot_ids = data.get("robot_ids", [])
                if isinstance(robot_ids, list):
                    for rid in robot_ids:
                        self.subscribed_robots.discard(rid)
        except json.JSONDecodeError:
            pass

    async def telemetry_update(self, event: dict[str, object]) -> None:
        # Forward telemetry updates from Redis flusher to WebSockets
        data = event.get("data")
        if isinstance(data, dict):
            filtered_data = {
                rid: state for rid, state in data.items() if rid in self.subscribed_robots
            }
            if filtered_data:
                await self.send(
                    text_data=json.dumps({"type": "telemetry_update", "data": filtered_data})
                )

    async def alert_notification(self, event: dict[str, object]) -> None:
        # Forward high-priority alerts to WebSockets
        data = event.get("data")
        if data:
            await self.send(text_data=json.dumps({"type": "alert", "payload": data}))
