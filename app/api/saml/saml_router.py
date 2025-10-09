import logging

import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.responses import JSONResponse, RedirectResponse
from starlette.status import (
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from config.constants import (
    AUTH_STATUS_COOKIE_NAME,
    ACCESS_TOKEN_COOKIE_NAME,
    LOG_CONFIG,
    URL_PAGE_HOME,
)
from config.settings import settings
from modules.auth.auth_jwt import get_token_from_request
from modules.saml.saml_service import saml_service
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

saml_router = APIRouter(prefix="/saml", tags=["SAML"])


@saml_router.get("/status")
async def get_saml_status():
    """
    Проверяет, включена ли SAML-аутентификация.

    :return: JSON с полем 'enabled', равным true, если SAML включен.
    """
    return JSONResponse(content={"enabled": saml_service.is_enabled()})


@saml_router.get("/sso")
async def sso(request: Request):
    """
    Инициирует процесс Single Sign-On.
    Перенаправляет пользователя на страницу входа IdP.

    :param request: Объект запроса FastAPI.
    :return: Редирект на страницу IdP.
    """
    if not saml_service.is_enabled():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="SAML is not configured"
        )
    try:
        auth = await saml_service.get_auth_for_request(request)
        # В RelayState можно передать URL, куда вернуть пользователя
        return_to = request.query_params.get("next", URL_PAGE_HOME)
        sso_url = auth.login(return_to=return_to)
        return RedirectResponse(url=sso_url)
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="SAML SSO error"
        )


@saml_router.post("/acs")
async def acs(request: Request, response: Response):
    """
    Assertion Consumer Service (ACS).
    Принимает SAML-ответ от IdP, обрабатывает его и создает сессию.

    :param request: Объект запроса FastAPI.
    :param response: Объект ответа FastAPI.
    :return: Редирект на целевую страницу.
    """
    if not saml_service.is_enabled():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="SAML is not configured"
        )
    try:
        return await saml_service.acs(request, response)
    except ValueError as e:
        logger.error(f"SAML ACS processing failed: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAML ACS processing error",
        )


@saml_router.get("/slo")
async def slo(request: Request):
    """
    Инициирует процесс Single Log-Out (SP-Initiated).
    Перенаправляет пользователя на страницу выхода IdP.

    :param request: Объект запроса FastAPI.
    :return: Редирект на страницу выхода IdP.
    """
    if not saml_service.is_enabled():
        # Эта проверка важна: если кто-то обратится к /saml/slo, когда SAML выключен,
        # мы не должны пытаться обработать это. Вместо этого, перенаправляем
        # на универсальный обработчик выхода.
        logger.warning(
            "SAML SLO endpoint was accessed, but SAML is disabled. Redirecting to final logout."
        )
        return RedirectResponse(
            url="/auth/logout/final", status_code=HTTP_307_TEMPORARY_REDIRECT
        )

    token = get_token_from_request(request)
    if not token:
        # Если токена нет, просто редиректим на страницу входа
        return RedirectResponse(url="/auth")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        name_id = payload.get("nameid")
        session_index = payload.get("sid")
        username = payload.get("sub", "<unknown>")

        if not name_id or not session_index:
            logger.warning(
                f"User '{username}' attempted SLO without SAML session info. Redirecting to final logout."
            )
            # Если нет данных для SAML SLO, перенаправляем на финальную очистку
            return RedirectResponse(
                url="/auth/logout/final", status_code=HTTP_307_TEMPORARY_REDIRECT
            )

        auth = await saml_service.get_auth_for_request(request)
        # В RelayState передаем URL, куда IdP должен вернуть нас после выхода
        base_url = str(request.base_url)
        return_to = f"{base_url.rstrip('/')}/saml/sls"
        slo_url = auth.logout(
            name_id=name_id, session_index=session_index, return_to=return_to
        )

        logger.info(
            f"User '{username}' initiated SAML SLO. Redirecting to IdP. return_to={return_to}"
        )
        return RedirectResponse(url=slo_url)

    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAML SLO initiation error",
        )


@saml_router.get("/sls")
async def sls(request: Request):
    """
    Single Logout Service (SLS).
    Принимает и обрабатывает LogoutResponse от IdP после выхода.

    :param request: Объект запроса FastAPI.
    :return: Редирект на страницу входа.
    """
    if not saml_service.is_enabled():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="SAML is not configured"
        )
    try:
        return await saml_service.slo(request)
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAML SLS processing error",
        )


@saml_router.get("/metadata")
async def metadata(request: Request):
    """
    Предоставляет метаданные Service Provider (SP).

    :param request: Объект запроса FastAPI.
    :return: XML с метаданными SP.
    """
    if not saml_service.is_enabled():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="SAML is not configured"
        )
    try:
        auth = await saml_service.get_auth_for_request(request)
        settings_data = auth.get_settings()
        sp_metadata = settings_data.get_sp_metadata()
        errors = settings_data.validate_metadata(sp_metadata)

        if errors:
            logger.error(f"SAML Metadata validation errors: {errors}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid SP metadata: {', '.join(errors)}",
            )

        return Response(content=sp_metadata, media_type="application/xml")
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="SAML Metadata error"
        )
