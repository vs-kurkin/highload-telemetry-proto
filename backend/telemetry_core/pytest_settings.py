import os

from .settings import *  # noqa: F403

# FORCE POSTGRES
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "telemetry_db"),
        "USER": os.getenv("DB_USER", "telemetry_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "supersecretpassword"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "TIME_ZONE": "UTC",
    }
}
