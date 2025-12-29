"""
WebSocket Token 认证中间件（DRF Token）

浏览器 WebSocket 无法像 HTTP 一样方便地附带 Authorization Header，
因此通过 querystring 传 token：
  ws(s)://host/ws/xxx/?token=xxxx

同时保留 AuthMiddlewareStack（cookie/session）作为兜底。
"""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_by_token(token_key: str):
    try:
        from rest_framework.authtoken.models import Token

        token = Token.objects.select_related("user").get(key=token_key)
        return token.user
    except Exception:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            query_string = scope.get("query_string", b"").decode("utf-8")
            qs = parse_qs(query_string)
            token_key = (qs.get("token") or [None])[0]
        except Exception:
            token_key = None

        if token_key:
            scope["user"] = await _get_user_by_token(token_key)

        return await super().__call__(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    # 先走 session/cookie（AuthMiddlewareStack 设置 scope["user"]），
    # 再用 token querystring 覆盖（如果提供了 token）。
    # 注意：middleware 执行顺序为“外层先执行 -> 调用内层”，
    # 因此 TokenAuthMiddleware 必须放在 AuthMiddlewareStack 的 *inner*，才能做到“token override”。
    return AuthMiddlewareStack(TokenAuthMiddleware(inner))


