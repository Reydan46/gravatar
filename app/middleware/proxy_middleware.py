import logging
import time
from typing import Dict

from starlette.types import ASGIApp, Receive, Scope, Send
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from config.constants import (
    LOG_CONFIG,
    PROXY_MIDDLEWARE_EXCLUDE_IPS,
    PROXY_MIDDLEWARE_LOG_THROTTLE_SECONDS,
)
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class ProxyMiddleware:
    """
    Middleware для обработки заголовков от прокси-сервера.
    Конфигурация полностью определяется свойством settings.trusted_proxy_ips_config.
    """

    def __init__(
        self,
        app: ASGIApp,
        log_throttle_seconds: int = PROXY_MIDDLEWARE_LOG_THROTTLE_SECONDS,
    ):
        """
        Инициализирует middleware.

        :param app: ASGI-приложение.
        :param log_throttle_seconds: Период в секундах, в течение которого
                                     повторные предупреждения от одного IP будут подавляться.
        """
        self.app = app
        self.config = settings.trusted_proxy_ips_config
        self.proxy_headers_app = ProxyHeadersMiddleware(app, trusted_hosts=self.config)
        self.log_throttle_seconds = log_throttle_seconds
        self.exclude_ips = set(PROXY_MIDDLEWARE_EXCLUDE_IPS)
        self._last_log_time_by_ip: Dict[str, float] = {}

    def _should_log(self, ip: str) -> bool:
        """
        Проверяет, нужно ли логировать предупреждение для данного IP.

        :param ip: IP-адрес источника.
        :return: True, если логирование разрешено.
        """
        if self.log_throttle_seconds <= 0:
            return True

        now = time.monotonic()
        last_log_time = self._last_log_time_by_ip.get(ip, 0)
        if now - last_log_time > self.log_throttle_seconds:
            self._last_log_time_by_ip[ip] = now
            return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Обрабатывает входящий запрос.

        :param scope: Информация о запросе ASGI.
        :param receive: Функция получения событий.
        :param send: Функция отправки событий.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_ip = scope.get("client", ("unknown", 0))[0]

        if client_ip in self.exclude_ips:
            await self.app(scope, receive, send)
            return

        if isinstance(self.config, list) and self.config:
            if client_ip not in self.config:
                headers = dict(scope.get("headers", []))
                proxy_header_keys = [
                    b"x-forwarded-for",
                    b"x-forwarded-proto",
                    b"x-forwarded-host",
                    b"x-real-ip",
                ]
                sent_proxy_headers = {
                    key.decode(): value.decode()
                    for key, value in headers.items()
                    if key.lower() in proxy_header_keys
                }

                if sent_proxy_headers and self._should_log(client_ip):
                    logger.warning(
                        f"[{client_ip}] Received proxy headers from an untrusted source. "
                        f"Headers will be ignored. Sent headers: {sent_proxy_headers}"
                    )

        await self.proxy_headers_app(scope, receive, send)
