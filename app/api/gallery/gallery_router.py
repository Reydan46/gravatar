import logging

import orjson
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.responses import FileResponse, RedirectResponse
from starlette.status import (
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_409_CONFLICT,
)

from api.crypto.crypto_schema import HybridEncryptedData
from api.gallery.gallery_schema import PaginatedAvatarsResponse
from config.constants import LOG_CONFIG
from modules.auth.auth_jwt import validate_jwt
from modules.auth.auth_permissions import Permissions, require_permission
from modules.crypto.operations.hybrid import decrypt_hybrid, encrypt_hybrid
from modules.gallery.gallery_service import get_paginated_avatars
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

gallery_router = APIRouter(prefix="/gallery", tags=["Gallery"])


@gallery_router.get("")
async def gallery_page(request: Request, response: Response):
    """
    Возвращает HTML-страницу галереи аватаров.

    Требует авторизации. Если пользователь не авторизован,
    перенаправляет на страницу входа.

    :param request: HTTP-запрос.
    :param response: HTTP-ответ.
    :return: HTML-страница или редирект.
    """
    try:
        await validate_jwt(request, response, auto_refresh=False)
        return FileResponse("static/gallery.html", media_type="text/html")
    except HTTPException:
        return RedirectResponse(
            url="/auth?next=/gallery", status_code=HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Gallery page error"
        )


@gallery_router.post("/data", response_model=dict)
async def get_gallery_data(
    request: Request,
    response: Response,
    payload: HybridEncryptedData,
):
    """
    Возвращает отфильтрованный и пагинированный список аватаров в зашифрованном виде.

    Требует права на просмотр галереи.

    :param request: HTTP-запрос.
    :param response: HTTP-ответ.
    :param payload: Зашифрованные параметры запроса.
    :return: Зашифрованный пагинированный список аватаров.
    """
    try:
        username, _ = await validate_jwt(request, response)
        require_permission(username, Permissions.GALLERY)

        try:
            decrypted_str = decrypt_hybrid(payload.model_dump())
        except ValueError:
            logger.warning(
                f"Decryption failed for user '{username}'. Keys may be outdated. Sending 409 Conflict."
            )
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Decryption failed. Client keys may be outdated.",
            )

        params = orjson.loads(decrypted_str)

        page = params.get("page", 1)
        page_size = params.get("pageSize", 10)
        filters = params.get("filters", {})
        active_filters = {k: v for k, v in filters.items() if v}

        # Получаем параметры сортировки из запроса
        sort_by = params.get("sortBy", "email")
        sort_dir = params.get("sortDir", "asc")

        paginated_data: PaginatedAvatarsResponse = get_paginated_avatars(
            page=page,
            page_size=page_size,
            filters=active_filters,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

        response_bytes = orjson.dumps(paginated_data.model_dump())
        response_json_str = response_bytes.decode("utf-8")

        encrypted_response = encrypt_hybrid(payload.model_dump(), response_json_str)
        return encrypted_response

    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching gallery data",
        )
