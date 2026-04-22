# ruff: noqa
"""Temporary docstring."""

from django.contrib import admin
from django.urls import include, path
from rest_framework import routers  # type: ignore[import-untyped]
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from robots.views import (
    AlertViewSet,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    DailyStatsViewSet,
    RobotViewSet,
    TelemetryViewSet,
)

router = routers.DefaultRouter()
router.register(r"robots", RobotViewSet)
router.register(r"alerts", AlertViewSet)
router.register(r"stats", DailyStatsViewSet)
router.register(r"telemetry", TelemetryViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("", include("django_prometheus.urls")),
]
