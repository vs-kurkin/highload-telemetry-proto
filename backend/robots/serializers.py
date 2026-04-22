# ruff: noqa
"""Temporary docstring."""

from rest_framework import serializers  # type: ignore[import-untyped]

from .models import Alert, Robot, Telemetry, TelemetryDailyStats


class DailyStatsSerializer(serializers.ModelSerializer):
    robot_id = serializers.ReadOnlyField(source="robot.robot_id")

    class Meta:
        model = TelemetryDailyStats
        fields = ["robot_id", "date", "avg_battery", "min_battery", "max_battery", "message_count"]


class RobotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Robot
        fields = ["robot_id", "status", "last_seen"]


class AlertSerializer(serializers.ModelSerializer):
    robot_id = serializers.ReadOnlyField(source="robot.robot_id")

    class Meta:
        model = Alert
        fields = ["id", "robot_id", "message", "created_at", "is_resolved"]


class TelemetrySerializer(serializers.ModelSerializer):
    robot_id = serializers.ReadOnlyField(source="robot.robot_id")

    class Meta:
        model = Telemetry
        fields = ["robot_id", "battery_lvl", "status", "timestamp"]
