# ruff: noqa
"""Temporary docstring."""

import logging

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Check for token in cookies first
        cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token")
        raw_token = request.COOKIES.get(cookie_name)

        # If not in cookies, fallback to default (Authorization header)
        if raw_token is None:
            header = self.get_header(request)
            if header is not None:
                raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
