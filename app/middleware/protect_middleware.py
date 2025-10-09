import logging
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN
from typing import Callable

from config.constants import LOG_CONFIG
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class HostAllowMiddleware:
    """
    Middleware для ограничения доступа только по разрешённым доменам/адресам из настроек

    :param app: ASGI-приложение
    """

    def __init__(self, app: Callable):
        """
        Инициализация middleware

        :param app: ASGI-приложение
        """
        self.app = app

    @staticmethod
    def _extract_host(headers: list[tuple[bytes, bytes]]) -> str:
        """
        Извлекает чистое (без порта) имя Host из ASGI-заголовков, приводит к нижнему регистру

        :param headers: Список заголовков [(key, value)]
        :return: Строка — домен или IP из Host-заголовка
        """
        for k, v in headers:
            if k == b"host":
                host = v.decode().split(":", 1)[0].strip().lower()
                return host
        return ""

    async def __call__(self, scope: dict, receive, send) -> None:
        """
        Проверяет заголовок Host на соответствие списку разрешённых; логирует все действия

        :param scope: Информация о запросе ASGI
        :param receive: Асинхронная функция получения событий ASGI
        :param send: Асинхронная функция отправки событий ASGI
        :return: None
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        host = self._extract_host(headers)
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        try:
            allowed_hosts = set(settings.allowed_hosts)
            if allowed_hosts and host not in allowed_hosts:
                logger.warning(f"[{client_ip}] Forbidden access host: {host}")
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Access denied"
                )

            await self.app(scope, receive, send)
        except HTTPException as e:
            res = JSONResponse({"detail": e.detail}, status_code=e.status_code)
            await res(scope, receive, send)
        except Exception:
            raise
