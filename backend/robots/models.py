# ruff: noqa
"""Temporary docstring."""

from typing import TYPE_CHECKING, Any

from django.db import models

from .constants import ROBOT_ID_MAX_LENGTH, STATUS_MAX_LENGTH

if TYPE_CHECKING:
    from datetime import date, datetime
    from django.db.models.manager import Manager

    class Robot(models.Model):
        robot_id: str
        status: str
        last_seen: datetime
        telemetry: Manager["Telemetry"]
        daily_stats: Manager["TelemetryDailyStats"]
        alerts: Manager["Alert"]

        def __str__(self) -> str: ...

    class Telemetry(models.Model):
        id: int
        robot: Robot
        robot_id: str
        battery_lvl: float
        status: str
        timestamp: datetime

        def __str__(self) -> str: ...

    class TelemetryDailyStats(models.Model):
        id: int
        robot: Robot
        robot_id: str
        date: date
        avg_battery: float
        min_battery: float
        max_battery: float
        message_count: int

        def __str__(self) -> str: ...

    class Alert(models.Model):
        id: int
        robot: Robot
        robot_id: str
        message: str
        created_at: datetime
        is_resolved: bool

        def __str__(self) -> str: ...
else:

    class Robot(models.Model):
        robot_id = models.CharField(max_length=ROBOT_ID_MAX_LENGTH, unique=True, primary_key=True)
        status = models.CharField(max_length=STATUS_MAX_LENGTH, default="UNKNOWN")
        last_seen = models.DateTimeField(auto_now=True)

        def __str__(self) -> str:
            return f"Robot {self.robot_id} ({self.status})"

    class Telemetry(models.Model):
        robot = models.ForeignKey(Robot, on_delete=models.CASCADE, related_name="telemetry")
        battery_lvl = models.FloatField()
        status = models.CharField(max_length=STATUS_MAX_LENGTH)
        timestamp = models.DateTimeField()

        class Meta:
            indexes = [
                models.Index(fields=["robot", "-timestamp"]),
            ]

        def __str__(self) -> str:
            return f"{self.robot.robot_id} - Battery: {self.battery_lvl}%"

    class TelemetryDailyStats(models.Model):
        robot = models.ForeignKey(Robot, on_delete=models.CASCADE, related_name="daily_stats")
        date = models.DateField(db_index=True)
        avg_battery = models.FloatField()
        min_battery = models.FloatField()
        max_battery = models.FloatField()
        message_count = models.IntegerField()

        class Meta:
            unique_together = ("robot", "date")
            verbose_name_plural = "Telemetry daily stats"

        def __str__(self) -> str:
            return f"{self.robot.robot_id} stats for {self.date}"

    class Alert(models.Model):
        robot = models.ForeignKey(Robot, on_delete=models.CASCADE, related_name="alerts")
        message = models.TextField()
        created_at = models.DateTimeField(auto_now_add=True)
        is_resolved = models.BooleanField(default=False)

        def __str__(self) -> str:
            return f"ALERT [{self.robot.robot_id}]: {self.message}"
