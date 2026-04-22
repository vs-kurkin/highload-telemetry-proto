# ruff: noqa
"""Temporary docstring."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Принимаем и ws/ и ws/telemetry/ для надежности
    re_path(r"^ws/$", consumers.TelemetryConsumer.as_asgi()),
    re_path(r"^ws/telemetry/$", consumers.TelemetryConsumer.as_asgi()),
]
