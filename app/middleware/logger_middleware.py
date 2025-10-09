import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, MutableMapping
from urllib.parse import urlparse

from starlette.types import ASGIApp, Receive, Scope, Send

from config.constants import (
    ADMIN_REFERER_EXCLUDE_TARGETS,
    ADMIN_REFERER_PATHS,
    LOG_CONFIG,
    REQUEST_LOGGING_EXCLUDE_PATHS,
)
from utils.session_context import session_id_var, suppress_app_logging_var

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

HTTP_499_CLIENT_CLOSED_REQUEST = 499


@dataclass
class RequestState:
    """Хранит состояние запроса для логирования"""

    scope: Scope
    start_time: float
    status_code: int = 0
    logged_close: bool = False

    def log_close(self) -> None:
        """
        Записывает лог о завершении запроса, если он еще не был записан
        """
        if self.logged_close:
            return

        status_code = self.status_code or HTTP_499_CLIENT_CLOSED_REQUEST
        method = self.scope["method"]
        path = self.scope.get("path", "")
        client = self.scope.get("client")
        client_ip = client[0] if client else "unknown"
        process_time = time.perf_counter() - self.start_time

        logger.debug(
            f"[{method}][CLOSE] {client_ip} - {path} [{status_code}][{process_time:.4f}s]"
        )
        self.logged_close = True


class RequestLoggingMiddleware:
    """
    Middleware для логирования HTTP-запросов с выводом времени обработки.
    Корректно измеряет полное время для обычных и потоковых ответов.
    """

    def __init__(self, app: ASGIApp, exclude_paths: list[str] = None):
        """
        Инициализирует Middleware

        :param app: ASGI-приложение
        :param exclude_paths: Список путей для исключения из логирования
        """
        self.app = app
        self.exclude_paths = exclude_paths or REQUEST_LOGGING_EXCLUDE_PATHS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Обрабатывает запрос, логируя его начало и гарантированное завершение.

        :param scope: Информация о запросе ASGI
        :param receive: Асинхронная функция получения событий ASGI
        :param send: Асинхронная функция отправки событий ASGI
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        suppress_app_logging_var.set(False)
        path = scope.get("path", "")
        should_log_request = True

        # Проверка по Referer-заголовку для условных исключений
        headers = dict(scope.get("headers", []))
        referer = headers.get(b"referer")
        if referer:
            try:
                referer_path = urlparse(referer.decode("utf-8")).path
                is_from_admin = any(
                    referer_path.startswith(p) for p in ADMIN_REFERER_PATHS
                )
                if is_from_admin:
                    is_noisy_target = any(
                        path.startswith(p) for p in ADMIN_REFERER_EXCLUDE_TARGETS
                    )
                    if is_noisy_target:
                        suppress_app_logging_var.set(True)
                        should_log_request = False
            except Exception as e:
                logger.warning(
                    f"Could not parse Referer header: {referer}. Error: {e}",
                    exc_info=True,
                )

        # Проверка по списку безусловных исключений
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            should_log_request = False

        session_id = uuid.uuid4().hex[:4]
        session_id_var.set(session_id)

        # Если по какой-либо причине логирование не требуется, просто передаем управление дальше
        if not should_log_request:
            await self.app(scope, receive, send)
            return

        state = RequestState(scope=scope, start_time=time.perf_counter())
        method = scope["method"]
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        logger.debug(f"[{method}][START] {client_ip} - {path}")

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            """
            Обертка над 'send' для отслеживания последнего сообщения

            :param message: ASGI-сообщение
            """
            if message["type"] == "http.response.start":
                state.status_code = message["status"]

            await send(message)

            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                state.log_close()

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Этот блок гарантирует запись лога для ответов без тела
            # (например, редиректов) или при разрыве соединения.
            state.log_close()
