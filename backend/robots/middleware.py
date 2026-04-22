# ruff: noqa
"""Temporary docstring."""

import logging
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from channels.db import database_sync_to_async  # type: ignore[import-untyped]
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from rest_framework_simplejwt.tokens import AccessToken  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            # 1. Try to get token from query string
            query_string = parse_qs(scope.get("query_string", b"").decode())
            token = query_string.get("token", [None])[0]

            # 2. If not in query string, try Cookies
            if not token:
                headers = dict(scope.get("headers", []))
                cookie_header = headers.get(b"cookie", b"").decode()

                cookie = SimpleCookie()
                cookie.load(cookie_header)

                auth_cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token")
                if auth_cookie_name in cookie:
                    token = cookie[auth_cookie_name].value

            if token:
                try:
                    access_token = AccessToken(token)
                    user_id = int(access_token["user_id"])
                    scope["user"] = await get_user(user_id)
                except Exception as e:
                    logger.error(f"JWT Auth Error: {e}")
                    scope["user"] = AnonymousUser()
            else:
                scope["user"] = AnonymousUser()
        except Exception as e:
            logger.error(f"Middleware Critical Error: {e}")
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
