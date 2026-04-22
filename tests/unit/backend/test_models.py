# ruff: noqa
"""Temporary docstring."""

from datetime import date

import pytest
from django.utils import timezone

from robots.models import Alert, Robot, Telemetry, TelemetryDailyStats


@pytest.mark.django_db
class TestModels:
    def test_robot_creation(self):
        robot, _ = Robot.objects.get_or_create(robot_id="R1_M1", defaults={"status": "OK"})
        assert str(robot) == "Robot R1_M1 (OK)"

    def test_telemetry_creation(self):
        robot, _ = Robot.objects.get_or_create(robot_id="R1_M2", defaults={"status": "OK"})
        now = timezone.now()
        telemetry = Telemetry.objects.create(robot=robot, battery_lvl=85.5, status="OK", timestamp=now)
        assert telemetry.robot.robot_id == "R1_M2"
        assert telemetry.battery_lvl == 85.5
        assert str(telemetry) == "R1_M2 - Battery: 85.5%"

    def test_alert_creation(self):
        robot, _ = Robot.objects.get_or_create(robot_id="R1_M3", defaults={"status": "OK"})
        alert = Alert.objects.create(robot=robot, message="Critical battery level")
        assert str(alert) == "ALERT [R1_M3]: Critical battery level"
        assert not alert.is_resolved

    def test_daily_stats_creation(self):
        robot, _ = Robot.objects.get_or_create(robot_id="R2_M1", defaults={"status": "OK"})
        today = date.today()
        stats = TelemetryDailyStats.objects.create(
            robot=robot,
            date=today,
            avg_battery=45.5,
            min_battery=10.0,
            max_battery=90.0,
            message_count=100,
        )
        assert stats.robot.robot_id == "R2_M1"
        assert stats.avg_battery == 45.5
        assert stats.min_battery == 10.0
        assert stats.max_battery == 90.0
        assert stats.message_count == 100
        assert str(stats) == f"R2_M1 stats for {today}"

    def test_robot_last_seen_updates(self):
        robot, _ = Robot.objects.get_or_create(robot_id="R3_M1", defaults={"status": "OK"})
        old_seen = robot.last_seen
        robot.status = "OFFLINE"
        robot.save()
        assert robot.last_seen >= old_seen
