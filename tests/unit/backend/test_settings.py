# ruff: noqa
"""Temporary docstring."""

from telemetry_core.settings import (
    DATABASES,
    INSTALLED_APPS,
    MIDDLEWARE,
    SECRET_KEY,
)

# Use SQLite in-memory for fast and reliable testing
DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

ROOT_URLCONF = "telemetry_core.urls"

# Redis test settings
REDIS_HOST = "localhost"
REDIS_PORT = 6379
DEFAULT_REDIS_PORT = 6379
REMOTE_HOST_IP = "127.0.0.1"

# Telemetry thresholds for testing
TIME_ZONE = "UTC"
USE_TZ = True
ALERT_BATTERY_THRESHOLD = 10.0
ALERT_THROTTLE_SECONDS = 0  # Disable throttling in tests for speed
TELEMETRY_FLUSH_INTERVAL = 0.1
TELEMETRY_BATCH_SIZE = 100
TELEMETRY_HISTORY_LIMIT = 1000
TELEMETRY_MAX_BUFFER_SIZE = 5000

# Disable django_prometheus for tests if not available
if "django_prometheus" in INSTALLED_APPS:
    INSTALLED_APPS.remove("django_prometheus")

if "django_prometheus.middleware.PrometheusBeforeMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("django_prometheus.middleware.PrometheusBeforeMiddleware")

if "django_prometheus.middleware.PrometheusAfterMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("django_prometheus.middleware.PrometheusAfterMiddleware")

# Authentication
SIMPLE_JWT = {
    "SIGNING_KEY": SECRET_KEY,
    "ALGORITHM": "HS256",
}

# MQTT
MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_SHARED_GROUP = None

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
