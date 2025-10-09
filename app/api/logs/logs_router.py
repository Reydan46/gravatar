import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic
from starlette.responses import FileResponse, RedirectResponse
from starlette.status import (
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from api.logs.logs_schema import LogFilterParams
from config.constants import LOG_CONFIG
from modules.auth.auth_jwt import validate_jwt
from modules.auth.auth_permissions import require_permission, Permissions
from modules.logs.logs_service import get_log_stream
from shared_memory.shm_shutdown import initialize_shutdown_shm, get_shutdown_flag
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

logs_router = APIRouter(prefix="/logs", tags=["Logs"])
security = HTTPBasic()


@logs_router.get(
    "",
    summary="Отображает страницу с логами",
    description="Показывает страницу для просмотра логов в режиме реального времени",
    response_class=HTMLResponse,
)
async def logs_page(request: Request, response: Response):
    """
    Возвращает HTML-страницу для просмотра логов в реальном времени

    Предоставляет интерфейс для мониторинга логов сервера, требует авторизации
    Если пользователь не авторизован, происходит перенаправление на страницу входа

    :param request: HTTP-запрос для анализа прав доступа пользователя
    :param response: HTTP-ответ, позволяет выдать страницу или выполнить редирект
    :return: HTML-страница просмотра логов
    """
    try:
        await validate_jwt(request, response, auto_refresh=False)
        return FileResponse("static/logs.html", media_type="text/html")
    except HTTPException:
        return RedirectResponse(
            url=f"/auth?next=/logs", status_code=HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Logs page error"
        )


@logs_router.get("/stream")
async def stream_logs(
    request: Request, response: Response, params: LogFilterParams = Depends()
):
    """
    Возвращает поток логов сервера в режиме реального времени через SSE

    Фильтрует логи по уровню, количеству и шаблону, отправляет данные через стрим в браузер
    Доступ предоставляется только авторизованным пользователям с нужными правами

    :param request: HTTP-запрос пользователя для проверки авторизации
    :param response: HTTP-ответ, используется для передачи стрима
    :param params: Параметры фильтрации логов (уровень, количество, шаблон)
    :return: Поток логов в формате Server-Sent Events
    """
    try:
        shm_shutdown, _ = initialize_shutdown_shm(False)
        if get_shutdown_flag(shm_shutdown):
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server is shutting down",
            )

        username, _ = await validate_jwt(request, response, auto_refresh=False)
        require_permission(username, Permissions.LOGS)

        return StreamingResponse(
            get_log_stream(username, params.limit),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Stream error"
        )
