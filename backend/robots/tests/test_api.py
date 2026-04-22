# ruff: noqa
"""Doc."""

from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status  # type: ignore[import-untyped]

from robots.models import Alert, Robot, TelemetryDailyStats


@pytest.mark.django_db
class TestRobotsAPI:
    def test_list_robots_unauthenticated(self, api_client):
        url = reverse("robot-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_robots_authenticated(self, api_client, test_user):
        Robot.objects.create(robot_id="R1", status="OK")
        api_client.force_authenticate(user=test_user)
        url = reverse("robot-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


@pytest.mark.django_db
class TestAlertsAPI:
    def test_resolve_alert(self, api_client, test_user):
        robot = Robot.objects.create(robot_id="R1", status="OK")
        alert = Alert.objects.create(robot=robot, message="Alert 1")
        api_client.force_authenticate(user=test_user)
        url = reverse("alert-resolve", kwargs={"pk": alert.pk})
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "alert resolved"


@pytest.mark.django_db
class TestDailyStatsAPI:
    def test_list_stats_filtering(self, api_client, test_user):
        robot1 = Robot.objects.create(robot_id="R1", status="OK")
        robot2 = Robot.objects.create(robot_id="R2", status="OK")
        today = date.today()
        TelemetryDailyStats.objects.create(
            robot=robot1,
            date=today,
            avg_battery=50.0,
            min_battery=0,
            max_battery=100,
            message_count=10,
        )
        TelemetryDailyStats.objects.create(
            robot=robot2,
            date=today,
            avg_battery=50.0,
            min_battery=0,
            max_battery=100,
            message_count=10,
        )

        api_client.force_authenticate(user=test_user)
        url = reverse("telemetrydailystats-list")

        # Test 1: No filter
        response = api_client.get(url)
        assert len(response.data) == 2

        # Test 2: Filter by robot_id
        response = api_client.get(url, {"robot_id": "R1"})
        assert len(response.data) == 1
        assert response.data[0]["robot_id"] == "R1"
