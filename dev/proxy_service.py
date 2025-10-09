import contextlib
import logging
import ssl
from typing import Any

# noinspection PyPackageRequirements
from aiohttp import ClientConnectionError, ClientSession, ClientTimeout, web

from config.constants import LOG_CONFIG
from config.settings import settings
from dev.ssl_tools import get_ssl_context

logger = logging.getLogger(LOG_CONFIG['main_logger_name'] + ".dev")


def is_stream_response(resp_headers: dict[str, Any]) -> bool:
    """
    Определяет, является ли ответ потоковым (stream), исходя из заголовков ответа

    :param resp_headers: Словарь заголовков HTTP-ответа
    :return: True, если ответ потоковый (streaming); False в противном случае
    """
    transfer_encoding = resp_headers.get("Transfer-Encoding", "").lower()
    content_type = resp_headers.get("Content-Type", "").lower()
    return (
            "chunked" in transfer_encoding
            or "text/event-stream" in content_type
            or "application/octet-stream" in content_type
    )


def prepare_proxy_headers(request: web.Request) -> dict[str, str]:
    """
    Формирует заголовки для проксируемого запроса, включая прокси-специфичные заголовки

    :param request: Объект входящего запроса aiohttp.web.Request
    :return: Словарь заголовков для запроса к upstream-серверу
    """
    headers = dict(request.headers)
    headers["Host"] = request.host
    headers["X-Real-IP"] = request.remote or ""
    prev_xff = headers.get("X-Forwarded-For", "")
    headers["X-Forwarded-For"] = ", ".join(filter(None, [prev_xff, request.remote or ""]))
    headers["X-Forwarded-Proto"] = "https"
    headers["X-Forwarded-Host"] = request.host
    if "Origin" in headers:
        headers["Origin"] = headers["Origin"]
    return headers


def split_response_headers(raw_headers: tuple[tuple[bytes, bytes], ...]) -> tuple[dict[str, str], list[str]]:
    """
    Разделяет исходные заголовки HTTP-ответа backend на обычные заголовки и отдельный список заголовков Set-Cookie

    :param raw_headers: Кортеж пар (ключ, значение) заголовков из исходного ответа backend
    :return: Кортеж: (словарь обычных заголовков, список строк Set-Cookie)
    """
    headers: dict[str, str] = {}
    set_cookies: list[str] = []
    for key, value in raw_headers:
        if key.lower() == b'set-cookie':
            set_cookies.append(value.decode('utf-8'))
        else:
            k, v = key.decode('utf-8'), value.decode('utf-8')
            if k in headers:
                # Объединяем дубликаты через запятую — общий http-стандарт (кроме set-cookie)
                headers[k] += f", {v}"
            else:
                headers[k] = v
    return headers, set_cookies


async def proxy_handler(request: web.Request) -> web.StreamResponse:
    """
    Проксирует запрос пользователя на FastAPI backend, корректно обрабатывая как потоковые, так и обычные ответы

    :param request: aiohttp.web.Request пользователя
    :return: Ответ пользователя (web.Response или web.StreamResponse)
    """
    upstream_url = f"http://127.0.0.1:{settings.app_port}{request.path_qs}"
    headers = prepare_proxy_headers(request)
    client_timeout = ClientTimeout(total=None, sock_read=600)
    data = request.content if request.can_read_body else None
    async with ClientSession(timeout=client_timeout) as session:
        async with session.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                params=request.query,
                data=data,
                allow_redirects=False,
                cookies=request.cookies,
        ) as resp:
            is_stream = is_stream_response(resp.headers)
            response_headers, set_cookie_headers = split_response_headers(resp.raw_headers)

            if not is_stream:
                body = await resp.read()
                proxy_response = web.Response(
                    status=resp.status,
                    headers=response_headers,
                    body=body
                )
                for cookie in set_cookie_headers:
                    proxy_response.headers.add('Set-Cookie', cookie)
                return proxy_response
            else:
                proxy_resp = web.StreamResponse(
                    status=resp.status,
                    headers=response_headers
                )
                for cookie in set_cookie_headers:
                    proxy_resp.headers.add('Set-Cookie', cookie)
                try:
                    await proxy_resp.prepare(request)
                    async for chunk in resp.content.iter_chunked(65536):
                        await proxy_resp.write(chunk)
                except (ClientConnectionError, ConnectionResetError, BrokenPipeError):
                    pass
                finally:
                    with contextlib.suppress(Exception):
                        await proxy_resp.write_eof()
                    return proxy_resp


@web.middleware
async def static_nocache_middleware(request: web.Request, handler) -> web.StreamResponse:
    """
    Устанавливает no-cache заголовки для ответов на запросы к /static/, чтобы отключить кэширование на стороне клиента

    :param request: aiohttp.web.Request пользователя
    :param handler: Следующая обрабатывающая функция
    :return: Ответ с установленными no-cache заголовками для статики (если применимо)
    """
    response = await handler(request)
    if request.path.startswith("/static/") and isinstance(response, web.StreamResponse):
        response.headers.update({
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Surrogate-Control": "no-store"
        })
    return response


def make_app() -> web.Application:
    """
    Создаёт экземпляр aiohttp-приложения с поддержкой статических файлов и обратного прокси

    :return: Инициализированный объект aiohttp.web.Application
    """
    app_ = web.Application(
        client_max_size=100 * 1024 ** 2,
        middlewares=[static_nocache_middleware]
    )
    app_.router.add_static("/static/", "./static", name="static", follow_symlinks=True, show_index=False)
    app_.router.add_route("*", "/{tail:.*}", proxy_handler)
    return app_


def run_proxy_server() -> None:
    """
    Запускает aiohttp-прокси сервер с поддержкой SSL, статики и потоковых ответов

    :return: None
    """
    cert_path, key_path = get_ssl_context()
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)

    logger.info(
        f"Proxy server running on https://0.0.0.0:{settings.nginx_port}, forwarding to 127.0.0.1:{settings.app_port}"
    )
    web.run_app(
        make_app(),
        host="0.0.0.0",
        port=settings.nginx_port,
        ssl_context=ssl_ctx,
        print=None
    )
