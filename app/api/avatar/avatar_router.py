import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from starlette.responses import StreamingResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from api.avatar.avatar_schema import AvatarParams
from config.constants import LOG_CONFIG
from modules.auth.auth_bearer import verify_api_key
from modules.avatar import avatar_service, avatar_sync_service
from utils.request_logging import log_request_error
from utils.session_context import suppress_app_logging_var

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

avatar_router = APIRouter(prefix="/avatar", tags=["Avatar"])


@avatar_router.post("/sync")
async def sync_avatars_stream(
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    Запускает синхронизацию аватаров из LDAP в потоковом режиме.

    Требует валидный API-ключ (passphrase) в заголовке Authorization.
    Возвращает поток Server-Sent Events (SSE).

    :param request: HTTP-запрос.
    :param api_key: Зависимость для проверки API-ключа.
    :return: Поток событий с состоянием синхронизации.
    """
    logger.info("Avatar synchronization triggered by API key.")
    try:
        return StreamingResponse(
            avatar_sync_service.sync_avatars_from_ldap_stream(),
            media_type="text/event-stream",
        )
    except Exception as e:
        log_request_error(request, e)
        # Для стриминга основной метод не должен вызывать HTTPException,
        # так как заголовки уже отправлены. Логика ошибок обрабатывается внутри генератора.
        # Этот блок остается как предохранитель на случай ошибок до начала стриминга.
        logger.error(f"Failed to initiate avatar sync stream: {e}", exc_info=True)
        # В реальной ситуации этот HTTPException может не сработать, если стриминг уже начался.
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred before sync stream started: {str(e)}",
        )


@avatar_router.get("/{image_hash}")
async def get_avatar(
    image_hash: str,
    request: Request,
):
    """
    Возвращает изображение аватара по его хешу.

    :param image_hash: MD5 или SHA256 хеш email.
    :param request: HTTP-запрос.
    :return: Изображение в формате JPEG.
    """
    try:
        query_params_dict = dict(request.query_params)
        params = AvatarParams.model_validate(query_params_dict)

        params_dict = params.model_dump(exclude_defaults=True)

        # Проверяем флаг, установленный в middleware через ContextVar
        if not suppress_app_logging_var.get():
            logger.info(
                f"Avatar requested for hash: {image_hash}, params: {params_dict}"
            )

        image_buffer = avatar_service.get_avatar_image(image_hash, params_dict)

        if image_buffer is None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Avatar not found"
            )

        return StreamingResponse(image_buffer, media_type="image/jpeg")

    except ValidationError as e:
        logger.warning(f"Invalid avatar request parameters: {e}")
        error_detail = e.errors()[0]
        # Формируем более читаемое сообщение
        msg = f"Invalid value for parameter '{error_detail['loc'][0]}': {error_detail['msg']}"
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    except ValueError as e:
        logger.warning(f"Invalid avatar request: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the avatar.",
        )
