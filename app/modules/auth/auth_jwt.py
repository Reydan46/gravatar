import logging
import time
from datetime import datetime
from typing import Optional

import jwt
from fastapi import HTTPException, Request, Response
from starlette.status import HTTP_401_UNAUTHORIZED

from config.constants import (
    TOKEN_MAX_AGE,
    ACCESS_TOKEN_COOKIE_NAME,
    AUTH_STATUS_COOKIE_NAME,
    LOG_CONFIG,
    TOKEN_RENEW_THRESHOLD_SECONDS,
    BOOT_TIME_COOKIE_NAME,
)

from config.settings import settings
from modules.auth.auth_base import AuthResult
from modules.auth.auth_fingerprint import (
    generate_fingerprint,
    decrypt_data_with_fingerprint,
    encrypt_data_with_fingerprint,
)
from shared_memory.shm_boot_time import get_boot_time

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def create_jwt_token(
    username: str,
    client_ip: str,
    expires_delta: int = TOKEN_MAX_AGE,
    old_token: Optional[str] = None,
    enc_data_fgp: Optional[str] = None,
    name_id: Optional[str] = None,
    session_index: Optional[str] = None,
) -> str:
    """
    Создает или обновляет JWT токен для пользователя. Сохраняет дату создания (iat) из оригинального токена.

    :param username: Имя пользователя
    :param client_ip: IP клиента
    :param expires_delta: Время жизни токена в секундах
    :param old_token: Оригинальный токен
    :param enc_data_fgp: Шифрованные данные отпечатком браузера
    :param name_id: NameID из SAML ответа
    :param session_index: SessionIndex из SAML ответа
    :return: JWT токен
    """
    if old_token:
        try:
            old_payload = jwt.decode(
                old_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            iat = old_payload.get("iat", time.time())
            # Сохраняем SAML-атрибуты при обновлении токена
            name_id = name_id or old_payload.get("nameid")
            session_index = session_index or old_payload.get("sid")
        except jwt.PyJWTError:
            iat = time.time()
    else:
        iat = time.time()

    payload = {
        "sub": username,
        "exp": time.time() + expires_delta,
        "iat": iat,
        "fgp": enc_data_fgp,
    }

    if name_id and session_index:
        payload["nameid"] = name_id
        payload["sid"] = session_index

    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    if old_token is None:
        log_msg = f"[{client_ip}][{username}] Created new JWT token"
        if session_index:
            log_msg += f" with SAML SessionIndex: {session_index}"
        logger.info(log_msg)
    else:
        logger.info(f"[{client_ip}][{username}] Updated JWT token")

    return token


def verify_jwt_token(token: str, fingerprint: str) -> tuple[AuthResult, dict | None]:
    """
    Проверяет JWT токен и возвращает результат аутентификации

    :param token: JWT токен для проверки
    :param fingerprint: Отпечаток браузера клиента
    :return: Результат аутентификации
    """
    username = "<unknown>"
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        username = payload.get("sub")
        if username is None:
            logger.warning("JWT token validation failed: missing username")
            return AuthResult(False, error_message="Неверный токен"), None

        enc_data_fgp = payload.get("fgp")
        if enc_data_fgp is None:
            logger.warning(
                f"[{username}] JWT token validation failed: missing fingerprint"
            )
            return AuthResult(False, error_message="Неверный токен"), None
        elif decrypt_data_with_fingerprint(fingerprint, enc_data_fgp) is None:
            logger.warning(
                f"[{username}] JWT token validation failed: mismatched fingerprint"
            )
            return AuthResult(False, error_message="Неверный токен"), None

        # Проверка срока действия токена
        exp = payload.get("exp")
        if exp is None:
            logger.warning("JWT token validation failed: missing expiration time")
            return AuthResult(False, error_message="Неверный токен"), None

        current_time = time.time()

        # Проверяем истек ли токен
        if current_time > exp:
            logger.warning(
                f"[{username}] JWT token expired: {datetime.fromtimestamp(exp).strftime('%Y.%m.%d %H:%M:%S')}"
            )
            return AuthResult(False, error_message="Токен истек"), None

        # Проверка наличия пользователя в списке users
        if not any(user.get("username") == username for user in settings.users):
            logger.warning(
                f"[{username}] JWT token validation failed: user not found in users"
            )
            return AuthResult(False, error_message="Доступ запрещен"), None

        return AuthResult(success=True, username=username), payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"[{username}] JWT token validation failed: token expired")
        return AuthResult(False, error_message="Токен истек"), None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT token validation failed: invalid token - {str(e)}")
        return AuthResult(False, error_message="Неверный токен"), None
    except jwt.PyJWTError as e:
        logger.warning(f"JWT token validation failed: {str(e)}")
        return AuthResult(False, error_message="Неверный токен"), None
    except Exception as e:
        logger.error(
            f"Unexpected error during JWT validation: {str(e)}, type: {type(e).__name__}"
        )
        return AuthResult(False, error_message="Неверный токен"), None


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Извлекает JWT токен из запроса (из куки или заголовка Authorization)

    :param request: Объект запроса
    :return: JWT токен или None, если токен не найден
    """
    # Сначала проверяем куки
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if token:
        return token

    # Затем проверяем заголовок Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")

    return None


def set_jwt_cookie(response: Response, token: str) -> None:
    """
    Устанавливает JWT токен в куки и дополнительную куку-индикатор с временем аутентификации

    :param response: Объект ответа
    :param token: JWT токен
    """
    # Текущее время
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S.%f")[:-3]

    # Основной токен - защищенный HttpOnly
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=TOKEN_MAX_AGE,
    )

    # Дополнительная кука-индикатор с временной меткой
    response.set_cookie(
        key=AUTH_STATUS_COOKIE_NAME,  # Дополнительная кука-индикатор
        value=current_time,  # Время выдачи токена
        httponly=False,  # Доступна для JavaScript
        secure=True,
        samesite="strict",
        max_age=TOKEN_MAX_AGE,
    )


async def validate_jwt(
    request: Request, response: Optional[Response] = None, auto_refresh: bool = True
) -> tuple[str, str]:
    """
    Проверяет JWT токен в запросе, валидирует cookie времени запуска сервера (boot_time), при необходимости обновляет cookie,
    а также автоматически обновляет токен при приближении срока действия (если передан response и auto_refresh=True).

    Если cookie BOOT_TIME_COOKIE_NAME отсутствует или отличается от текущего boot_time сервера (полученного из shared memory),
    на клиент будет установлена актуальная cookie (response.set_cookie).

    При необходимости (автоматическое продление токена по времени жизни) обновляет JWT токен в cookie.

    :param request: Объект запроса
    :param response: Объект ответа для обновления токена или куки boot_time
    :param auto_refresh: Обновить ли токен автоматически (по истечению времени жизни)
    :return: Кортеж (имя пользователя, токен)
    :raises HTTPException: Если токен отсутствует или недействителен, либо fingerprint не совпал
    """
    client_ip = request.client.host
    token = get_token_from_request(request)
    if not token:
        logger.warning(f"[{client_ip}] JWT validation failed: no token provided")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Authentication required",
                    "type": "authentication_error",
                    "code": "token_missing",
                }
            },
        )

    current_fingerprint = generate_fingerprint(request.headers)
    auth_result, jwt_payload = verify_jwt_token(token, current_fingerprint)
    if not auth_result.success:
        logger.warning(
            f"[{client_ip}] JWT validation failed: {auth_result.error_message}"
        )
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid or expired token",
                    "type": "authentication_error",
                    "code": "invalid_token",
                }
            },
        )

    # Проверка и обновление boot_time cookie
    current_boot_time = get_boot_time()
    client_boot_cookie = request.cookies.get(BOOT_TIME_COOKIE_NAME)
    try:
        client_boot_cookie_float = (
            float(client_boot_cookie) if client_boot_cookie is not None else None
        )
    except (TypeError, ValueError):
        client_boot_cookie_float = None
    if response is not None and (
        client_boot_cookie_float is None
        or current_boot_time != client_boot_cookie_float
    ):
        response.set_cookie(
            key=BOOT_TIME_COOKIE_NAME,
            value=str(current_boot_time),
            httponly=False,  # Доступна для JavaScript
            secure=True,
            samesite="strict",
        )

    # Автоматическое обновление токена, если предоставлен объект ответа
    if response and auto_refresh:
        try:
            exp = jwt_payload.get("exp")
            if exp is not None and (exp - time.time()) <= TOKEN_RENEW_THRESHOLD_SECONDS:
                client_ip = request.client.host
                data_fgp = {
                    "username": auth_result.username,
                    "client_ip": client_ip,
                    "current_time": int(time.time()),
                }
                enc_data_fgp = encrypt_data_with_fingerprint(request.headers, data_fgp)
                token = create_jwt_token(
                    auth_result.username,
                    client_ip=client_ip,
                    old_token=token,
                    enc_data_fgp=enc_data_fgp,
                )
                set_jwt_cookie(response, token)
        except Exception as e:
            logger.error(
                f"[{client_ip}] Failed to check token expiration for auto-refresh: {e}"
            )

    return auth_result.username, token


def get_username_from_token(token: Optional[str]) -> str:
    """
    Извлекает имя пользователя из JWT токена

    :param token: JWT токен
    :return: Имя пользователя или '<unknown>'
    """
    if not token:
        return "<unknown>"
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub", "<unknown>")
    except Exception:
        return "<unknown>"
