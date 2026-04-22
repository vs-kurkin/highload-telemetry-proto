# ruff: noqa
"""Temporary docstring."""

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.pagination import LimitOffsetPagination  # type: ignore[import-untyped]
from rest_framework import permissions, status, viewsets  # type: ignore[import-untyped]
from rest_framework.decorators import action  # type: ignore[import-untyped]
from rest_framework.response import Response  # type: ignore[import-untyped]
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Alert, Robot, TelemetryDailyStats, Telemetry
from .serializers import AlertSerializer, DailyStatsSerializer, RobotSerializer, TelemetrySerializer


class TelemetryPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 1000


class TelemetryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Telemetry.objects.all().order_by("-timestamp")
    serializer_class = TelemetrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TelemetryPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        robot_id = self.request.query_params.get("robot_id")
        start_time = self.request.query_params.get("start_time")
        end_time = self.request.query_params.get("end_time")

        if robot_id:
            queryset = queryset.filter(robot_id=robot_id)
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)

        return queryset


class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")

            simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})

            # Set HttpOnly Cookies
            response.set_cookie(
                key=simple_jwt_settings.get("AUTH_COOKIE", "access_token"),
                value=access_token,
                httponly=True,
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", False),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=int(simple_jwt_settings.get("ACCESS_TOKEN_LIFETIME").total_seconds()),
            )
            response.set_cookie(
                key=simple_jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"),
                value=refresh_token,
                httponly=True,
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", False),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=int(simple_jwt_settings.get("REFRESH_TOKEN_LIFETIME").total_seconds()),
            )
            # Remove tokens from response body for security
            del response.data["access"]
            del response.data["refresh"]

        return response


class RobotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Robot.objects.all().order_by("robot_id")
    serializer_class = RobotSerializer
    permission_classes = [permissions.IsAuthenticated]


@method_decorator(csrf_exempt, name="dispatch")
class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.filter(is_resolved=False).order_by("-created_at")
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        # Explicitly check for already resolved or non-existent alerts
        alert = Alert.objects.filter(pk=pk).first()
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


class DailyStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelemetryDailyStats.objects.all().order_by("-date")
    serializer_class = DailyStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        robot_id = self.request.query_params.get("robot_id")
        if robot_id:
            queryset = queryset.filter(robot_id=robot_id)
        return queryset
