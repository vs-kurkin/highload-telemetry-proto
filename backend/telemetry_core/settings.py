# ruff: noqa
"""Temporary docstring."""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe")
DEBUG = True
ALLOWED_HOSTS = ["*"]
REMOTE_HOST_IP = os.getenv("REMOTE_HOST_IP", "127.0.0.1")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_prometheus",
    "robots",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("robots.authentication.CookieJWTAuthentication",)
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_REFRESH": "refresh_token",
    "AUTH_COOKIE_DOMAIN": None,
    "AUTH_COOKIE_SECURE": False,
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_SAMESITE": "Lax",
}

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    f"http://{REMOTE_HOST_IP}:3000",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [f"http://{REMOTE_HOST_IP}:3000", "http://localhost:3000"]

ROOT_URLCONF = "telemetry_core.urls"
ASGI_APPLICATION = "telemetry_core.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "telemetry_db"),
        "USER": os.getenv("DB_USER", "telemetry_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "supersecretpassword"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("redis", 6379)]},
    },
}

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Logic Thresholds
TELEMETRY_FLUSH_INTERVAL = 0.1
TELEMETRY_BATCH_SIZE = 1000
TELEMETRY_MAX_BUFFER_SIZE = 50000
TELEMETRY_HISTORY_LIMIT = 10000

ALERT_BATTERY_THRESHOLD = 20.0
ALERT_THROTTLE_SECONDS = 600

MQTT_SHARED_GROUP = None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = "UTC"
USE_TZ = True
