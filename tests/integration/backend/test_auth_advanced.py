# ruff: noqa
import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from django.conf import settings
from robots.models import Robot, TelemetryDailyStats, Alert
from datetime import date


@pytest.mark.django_db
def test_cookie_auth_flow(api_client, test_user):
    # 1. Login via view to get cookies
    login_url = reverse("token_obtain_pair")
    response = api_client.post(login_url, {"username": "testuser", "password": "password123"})

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    assert "access" not in response.data

    # 2. Access protected endpoint using cookie (automatically handled by api_client if we don't clear cookies)
    # But for clarity, we verify it works without Manual Authorization header
    robots_url = reverse("robot-list")
    response = api_client.get(robots_url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_cookie_auth_failure_invalid_token(api_client):
    api_client.cookies["access_token"] = "invalid-token"
    url = reverse("robot-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_daily_stats_filter(api_client, test_user):
    api_client.force_authenticate(user=test_user)

    Robot.objects.create(robot_id="R1")
    Robot.objects.create(robot_id="R2")
    TelemetryDailyStats.objects.create(
        robot_id="R1", date=date.today(), avg_battery=80.0, max_battery=90.0, min_battery=70.0, message_count=10
    )
    TelemetryDailyStats.objects.create(
        robot_id="R2", date=date.today(), avg_battery=50.0, max_battery=60.0, min_battery=40.0, message_count=5
    )

    url = reverse("telemetrydailystats-list")

    # Test without filter
    response = api_client.get(url)
    assert len(response.data) == 2

    # Test with filter
    response = api_client.get(url, {"robot_id": "R1"})
    assert len(response.data) == 1
    assert response.data[0]["robot_id"] == "R1"


@pytest.mark.django_db
def test_alert_resolve_logic(api_client, test_user):
    api_client.force_authenticate(user=test_user)

    robot = Robot.objects.create(robot_id="R1")
    alert = Alert.objects.create(robot=robot, message="Test alert")
    url = reverse("alert-resolve", kwargs={"pk": alert.pk})

    # Resolve first time
    response = api_client.post(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "alert resolved"

    # Resolve second time
    response = api_client.post(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "already_resolved"

    # Resolve non-existent
    url_fake = reverse("alert-resolve", kwargs={"pk": 9999})
    response = api_client.post(url_fake)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "not_found_or_resolved"


@pytest.mark.django_db
def test_alert_resolve_db_error(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    robot = Robot.objects.create(robot_id="R1")
    alert = Alert.objects.create(robot=robot, message="Test alert")
    url = reverse("alert-resolve", kwargs={"pk": alert.pk})

    with patch("robots.models.Alert.save", side_effect=Exception("DB Error")):
        response = api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "db_error"


@pytest.mark.django_db
def test_jwt_fallback_to_header(api_client, test_user, api_token):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {api_token}")
    url = reverse("robot-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_no_credentials_at_all(api_client):
    url = reverse("robot-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
