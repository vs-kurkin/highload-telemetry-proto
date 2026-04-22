# ruff: noqa
"""Temporary docstring."""

import os

from channels.routing import ProtocolTypeRouter, URLRouter  # type: ignore[import-untyped]
from channels.security.websocket import AllowedHostsOriginValidator  # type: ignore[import-untyped]
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "telemetry_core.settings")

# get_asgi_application() calls django.setup(), which is required before importing models/middleware
django_asgi_app = get_asgi_application()

import robots.routing  # noqa: E402
from robots.middleware import JwtAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JwtAuthMiddleware(URLRouter(robots.routing.websocket_urlpatterns))
        ),
    }
)
