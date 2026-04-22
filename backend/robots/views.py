# ruff: noqa
"""
Views for Robots app.
Includes custom JWT views for HttpOnly Cookie authentication.
"""

from typing import Any, cast, TYPE_CHECKING

from django.conf import settings
from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

if TYPE_CHECKING:
    from datetime import timedelta

from .models import Alert, Robot, Telemetry, TelemetryDailyStats
from .serializers import (
    AlertSerializer,
    DailyStatsSerializer,
    RobotSerializer,
    TelemetrySerializer,
)

class TelemetryPagination(LimitOffsetPagination):
    default_limit: int = 100
    max_limit: int = 1000

class TelemetryViewSet(viewsets.ReadOnlyModelViewSet[Telemetry]):
    queryset: QuerySet[Telemetry] = Telemetry.objects.all().order_by("-timestamp")
    serializer_class = TelemetrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TelemetryPagination

    def get_queryset(self) -> QuerySet[Telemetry]:
        queryset: QuerySet[Telemetry] = super().get_queryset()
        robot_id: str | None = self.request.query_params.get("robot_id")
        start_time: str | None = self.request.query_params.get("start_time")
        end_time: str | None = self.request.query_params.get("end_time")

        if robot_id:
            queryset = queryset.filter(robot_id=robot_id)
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)

        return queryset

def get_token_lifetime(key: str, default_seconds: int) -> int:
    """Helper to safely get token lifetime from settings."""
    jwt_settings = getattr(settings, "SIMPLE_JWT", {})
    lifetime = jwt_settings.get(key)
    if hasattr(lifetime, "total_seconds"):
        return int(lifetime.total_seconds())
    return default_seconds

class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response: Response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access_token: str | None = response.data.get("access")
            refresh_token: str | None = response.data.get("refresh")
            simple_jwt_settings: dict[str, Any] = getattr(settings, "SIMPLE_JWT", {})

            response.set_cookie(
                key=simple_jwt_settings.get("AUTH_COOKIE", "access_token"),
                value=cast(str, access_token),
                httponly=True,
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", False),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=get_token_lifetime("ACCESS_TOKEN_LIFETIME", 3600),
            )
            response.set_cookie(
                key=simple_jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"),
                value=cast(str, refresh_token),
                httponly=True,
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", False),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=get_token_lifetime("REFRESH_TOKEN_LIFETIME", 86400),
            )
            del response.data["access"]
            del response.data["refresh"]

        return response

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        refresh_token = request.COOKIES.get(getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_REFRESH", "refresh_token"))
        if refresh_token:
            request.data["refresh"] = refresh_token
        
        response: Response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            access_token: str | None = response.data.get("access")
            refresh_token_new: str | None = response.data.get("refresh")
            simple_jwt_settings: dict[str, Any] = getattr(settings, "SIMPLE_JWT", {})

            response.set_cookie(
                key=simple_jwt_settings.get("AUTH_COOKIE", "access_token"),
                value=cast(str, access_token),
                httponly=True,
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", False),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=get_token_lifetime("ACCESS_TOKEN_LIFETIME", 3600),
            )
            
            if refresh_token_new:
                response.set_cookie(
                    key=simple_jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"),
                    value=cast(str, refresh_token_new),
                    httponly=True,
                    secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", False),
                    samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                    max_age=get_token_lifetime("REFRESH_TOKEN_LIFETIME", 86400),
                )
            
            if "access" in response.data: del response.data["access"]
            if "refresh" in response.data: del response.data["refresh"]

        return response

class RobotViewSet(viewsets.ReadOnlyModelViewSet[Robot]):
    queryset: QuerySet[Robot] = Robot.objects.all().order_by("robot_id")
    serializer_class = RobotSerializer
    permission_classes = [permissions.IsAuthenticated]

@method_decorator(csrf_exempt, name="dispatch")
class AlertViewSet(viewsets.ModelViewSet[Alert]):
    queryset: QuerySet[Alert] = Alert.objects.filter(is_resolved=False).order_by("-created_at")
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def resolve(self, request: Request, pk: Any = None) -> Response:
        alert: Alert | None = Alert.objects.filter(pk=pk).first()
        if not alert:
            return Response({"status": "not_found_or_resolved"}, status=status.HTTP_200_OK)

        if alert.is_resolved:
            return Response({"status": "already_resolved"}, status=status.HTTP_200_OK)

        try:
            alert.is_resolved = True
            alert.save()
            return Response({"status": "alert resolved"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "db_error"}, status=status.HTTP_400_BAD_REQUEST)

class DailyStatsViewSet(viewsets.ReadOnlyModelViewSet[TelemetryDailyStats]):
    queryset: QuerySet[TelemetryDailyStats] = TelemetryDailyStats.objects.all().order_by("-date")
    serializer_class = DailyStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet[TelemetryDailyStats]:
        queryset: QuerySet[TelemetryDailyStats] = super().get_queryset()
        robot_id: str | None = self.request.query_params.get("robot_id")
        if robot_id:
            queryset = queryset.filter(robot_id=robot_id)
        return queryset
