import logging
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class LoggingCORSMiddleware:
    """
    Middleware-обёртка над стандартным CORSMiddleware с логированием заблокированных Origin

    :param app: ASGI-приложение
    :param allow_origins: Список разрешённых Origin
    :return: None
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str] = None,
        allow_methods=None,
        allow_headers=None,
        allow_credentials: bool = False,
        allow_origin_regex: str = None,
        expose_headers=None,
        max_age: int = 600,
    ):
        self.allow_origins = allow_origins or []
        self._inner = CORSMiddleware(
            app,
            allow_origins=allow_origins or [],
            allow_methods=allow_methods or ["*"],
            allow_headers=allow_headers or ["*"],
            allow_credentials=allow_credentials,
            allow_origin_regex=allow_origin_regex,
            expose_headers=expose_headers,
            max_age=max_age,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Логирует заблокированные Origin при помощи CORSMiddleware

        :param scope: Информация о запросе ASGI
        :param receive: Функция получения событий
        :param send: Функция отправки событий
        :return: None
        """
        if scope["type"] != "http":
            await self._inner(scope, receive, send)
            return

        headers_dict = dict(scope.get("headers", []))
        origin = headers_dict.get(b"origin")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        if origin:
            origin_val = origin.decode()
            if (
                self.allow_origins
                and "*" not in self.allow_origins
                and origin_val not in self.allow_origins
            ):
                logger.warning(f"[{client_ip}] CORS blocked, origin: {origin_val}")

        await self._inner(scope, receive, send)
