import logging
from enum import Enum

from fastapi import Request
from typing import Dict, Any

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def log_request_parameters(params: Dict[str, Any] = None) -> None:
    """
    Логирует информацию о запросе

    :param params: Параметры для логирования
    """
    log_message = "Parameters:"

    def val_to_str(val: Any) -> str:
        """
        Преобразует значение в строку с поддержкой Enum

        :param val: Значение
        :return: Строковое представление значения
        """
        if isinstance(val, Enum):
            return val.value
        return str(val)

    if params:
        log_message += " ["
        log_message += ", ".join(
            f"{key}: {val_to_str(value)}" for key, value in params.items()
        )
        log_message += "]"

    logger.info(log_message)


def log_request_error(request: Request, e: Exception) -> None:
    """
    Логирует информацию об ошибке запроса

    :param request: Объект запроса
    :param e: Объект исключения
    """
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    logger.error(
        f"[ERROR][{method}] {client_ip} - {path} - {type(e).__name__}: {str(e)}"
    )
