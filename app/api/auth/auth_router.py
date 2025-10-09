import logging

from fastapi import APIRouter, Request, Response, HTTPException
from starlette.responses import FileResponse, RedirectResponse
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_307_TEMPORARY_REDIRECT,
)
import jwt

from api.crypto.crypto_schema import EncryptedData
from api.logs.logs_schema import AuthResponse, TokenResponse
from config.constants import (
    ACCESS_TOKEN_COOKIE_NAME,
    AUTH_STATUS_COOKIE_NAME,
    LOG_CONFIG,
)
from config.settings import settings
from modules.auth.auth_flow import auth_login_flow
from modules.auth.auth_jwt import (
    validate_jwt,
    get_token_from_request,
    get_username_from_token,
)
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

auth_router: APIRouter = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.get("", response_class=FileResponse)
async def auth_page(request: Request):
    """
    Возвращает HTML-страницу с формой авторизации пользователя

    Форма используется для ввода логина и пароля и последующей аутентификации
    Обеспечивает начальный шаг входа в систему

    :param request: HTTP-запрос с параметрами обращения
    :return: Страница авторизации с формой входа
    """
    try:
        return FileResponse("static/auth.html", media_type="text/html")
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth page error"
        )


@auth_router.post("/login", response_model=AuthResponse)
async def auth_login(request: Request, response: Response, auth_data: EncryptedData):
    """
    Выполняет аутентификацию пользователя по зашифрованным данным

    Расшифровывает входные данные и проверяет учетные данные пользователя
    В случае успеха устанавливает куки с токеном, при ошибке возвращает статус и причину

    :param request: HTTP-запрос пользователя
    :param response: HTTP-ответ для установки кук
    :param auth_data: Зашифрованная информация для входа
    :return: Статус аутентификации и сообщение результата
    """
    try:
        auth_result = await auth_login_flow(request, auth_data, response)
        if auth_result.success:
            return {"status": "success", "message": "Авторизация успешна"}
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail=auth_result.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth data error"
        )


@auth_router.post("/check_token", response_model=TokenResponse)
async def check_token(request: Request, response: Response):
    """
    Проверяет валидность и актуальность JWT токена пользователя

    Используется для подтверждения авторизации текущей сессии пользователя
    Возвращает статус проверки и поясняющее сообщение

    :param request: HTTP-запрос пользователя
    :param response: HTTP-ответ для возможной передачи обновленного токена
    :return: Информация о статусе токена и сообщение результата
    """
    try:
        await validate_jwt(request, response)
        return {"status": "success", "message": "Токен валиден"}
    except HTTPException:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Недействительный токен"
        )
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Check token error"
        )


@auth_router.post("/refresh_token", response_model=AuthResponse)
async def refresh_token(request: Request, response: Response):
    """
    Обновляет действующий JWT токен пользователя при необходимости

    Проверяет токен из запроса и выдает новый токен, если истекло его действие
    Возвращает результат обновления и сопутствующее сообщение

    :param request: HTTP-запрос пользователя с cookie или заголовком токена
    :param response: HTTP-ответ для передачи нового токена
    :return: Статус обновления токена и сообщение о результате
    """
    try:
        _, new_token = await validate_jwt(request, response)
        old_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
        return {
            "status": "success",
            "message": (
                "Токен обновлен" if old_token != new_token else "Токен не обновлен"
            ),
        }
    except HTTPException:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Недействительный токен"
        )
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Refresh token error"
        )


@auth_router.get("/logout", name="logout")
async def logout(request: Request):
    """
    Осуществляет выход пользователя из сессии.
    Определяет тип пользователя (SAML или обычный) и выполняет
    соответствующий процесс выхода.

    :param request: HTTP-запрос
    :return: RedirectResponse, инициирующий выход.
    """
    client_ip = request.client.host
    token = get_token_from_request(request)

    if not token:
        logger.info(
            f"[{client_ip}] Logout attempt without token. Redirecting to /auth."
        )
        return RedirectResponse(url="/auth", status_code=HTTP_307_TEMPORARY_REDIRECT)

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except jwt.PyJWTError:
        payload = {}

    username = payload.get("sub", "<unknown>")
    is_saml_user = "sid" in payload and "nameid" in payload
    saml_enabled = settings.saml_options.get("enabled", False)

    if is_saml_user and saml_enabled:
        logger.info(
            f"[{client_ip}][{username}] SAML user logout initiated. Redirecting to SLO endpoint."
        )
        return RedirectResponse(
            url="/saml/slo", status_code=HTTP_307_TEMPORARY_REDIRECT
        )
    else:
        if is_saml_user and not saml_enabled:
            logger.info(
                f"[{client_ip}][{username}] SAML user logging out, but SAML is disabled. Proceeding with local logout."
            )
        else:
            logger.info(
                f"[{client_ip}][{username}] Standard user logout initiated. Proceeding with local logout."
            )
        return RedirectResponse(
            url="/auth/logout/final", status_code=HTTP_307_TEMPORARY_REDIRECT
        )


@auth_router.get("/logout/final", name="logout_final")
async def logout_final(request: Request):
    """
    Финальный эндпоинт выхода. Гарантированно удаляет cookie
    и перенаправляет на страницу входа.

    :param request: HTTP-запрос
    :return: RedirectResponse на страницу входа
    """
    client_ip = request.client.host
    token = get_token_from_request(request)
    username = get_username_from_token(token)

    logger.info(
        f"[{client_ip}][{username}] Finalizing logout. Clearing cookies and redirecting to /auth."
    )

    response = RedirectResponse(url="/auth", status_code=HTTP_307_TEMPORARY_REDIRECT)
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE_NAME)
    response.delete_cookie(key=AUTH_STATUS_COOKIE_NAME)
    return response
