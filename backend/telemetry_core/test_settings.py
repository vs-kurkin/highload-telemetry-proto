# ruff: noqa
from typing import Any, Dict

from .settings import *

DATABASES: Dict[str, Dict[str, Any]] = {  # type: ignore[no-redef]
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
        "TIME_ZONE": "UTC",
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {},
    }
}

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django_prometheus"]
MIDDLEWARE = [m for m in MIDDLEWARE if "prometheus" not in m.lower()]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
