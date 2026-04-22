# ruff: noqa
"""Temporary docstring."""

from django.contrib import admin

from .models import Alert, Robot, Telemetry


@admin.register(Robot)
class RobotAdmin(admin.ModelAdmin):
    list_display = ("robot_id", "status", "last_seen")
    search_fields = ("robot_id",)


@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ("robot", "battery_lvl", "status", "timestamp")
    list_filter = ("status", "robot")
    search_fields = ("robot__robot_id",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("robot", "message", "created_at", "is_resolved")
    list_filter = ("is_resolved", "robot")
    search_fields = ("robot__robot_id", "message")
