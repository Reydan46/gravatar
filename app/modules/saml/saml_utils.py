import logging
from typing import Any, Dict

from fastapi import Request

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


async def prepare_fastapi_request_for_saml(request: Request) -> Dict[str, Any]:
    """
    Подготавливает данные запроса FastAPI для использования с библиотекой python3-saml.

    :param request: Объект запроса FastAPI.
    :return: Словарь, совместимый с python3-saml.
    """
    form_data = {}
    if request.method == "POST":
        try:
            # FormData может быть MultiDict, преобразуем в обычный dict
            form_data = dict(await request.form())
        except Exception as e:
            logger.warning(
                f"Could not parse form data for SAML request: {e}", exc_info=False
            )

    # Определяем схему (http/https) с учетом заголовков от reverse proxy
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    https = "on" if proto == "https" else "off"

    # Определяем хост с учетом заголовков от reverse proxy
    host_header = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host_header:
        host_header = request.url.netloc  # Fallback

    host_parts = host_header.split(":", 1)
    http_host = host_parts[0]

    # Определяем порт с учетом заголовков от reverse proxy
    port_str = request.headers.get("x-forwarded-port")
    if not port_str:
        if len(host_parts) > 1:
            port_str = host_parts[1]
        else:
            # Если порт не указан в заголовке, используем стандартный для схемы
            port_str = "443" if https == "on" else "80"

    return {
        "https": https,
        "http_host": http_host,
        "server_port": port_str,
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": form_data,
        "query_string": request.url.query,
    }
