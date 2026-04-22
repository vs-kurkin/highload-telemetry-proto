# ruff: noqa
"""Temporary docstring."""

import orjson
from typing import TYPE_CHECKING, Any, Final

from channels.generic.websocket import AsyncWebsocketConsumer

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User

from .constants import OPERATORS_GROUP_NAME

class TelemetryConsumer(AsyncWebsocketConsumer):
    group_name: str
    subscribed_robots: set[str]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.subscribed_robots = set()

    async def connect(self) -> None:
        user: User | AnonymousUser = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        self.group_name = OPERATORS_GROUP_NAME
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str) -> None:
        try:
            data: dict[str, Any] = orjson.loads(text_data)
            action: str | None = data.get("action")
            
            if action == "subscribe":
                s_robot_ids: list[str] = data.get("robot_ids", [])
                if isinstance(s_robot_ids, list):
                    self.subscribed_robots.update(map(str, s_robot_ids))
            elif action == "unsubscribe":
                u_robot_ids: list[str] = data.get("robot_ids", [])
                if isinstance(u_robot_ids, list):
                    for rid in u_robot_ids:
                        self.subscribed_robots.discard(str(rid))
        except Exception:
            pass

    async def telemetry_update(self, event: dict[str, Any]) -> None:
        data: dict[str, dict[str, Any]] | None = event.get("data")
        if isinstance(data, dict):
            filtered_data: dict[str, dict[str, Any]] = {
                rid: state for rid, state in data.items() if rid in self.subscribed_robots
            }
            if filtered_data:
                await self.send(
                    text_data=orjson.dumps({"type": "telemetry_update", "data": filtered_data}).decode()
                )

    async def alert_notification(self, event: dict[str, Any]) -> None:
        data: Any = event.get("data")
        if data:
            await self.send(text_data=orjson.dumps({"type": "alert", "payload": data}).decode())
