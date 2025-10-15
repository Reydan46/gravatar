import logging
import time

from fastapi import Request, Response
from fastapi.security import HTTPBasicCredentials

from api.crypto.crypto_schema import EncryptedData
from config.constants import LOG_CONFIG
from modules.auth.auth_base import AuthResult
from modules.auth.auth_basic import validate_credentials
from modules.auth.auth_bruteforce import is_ip_locked, process_failed_attempt
from modules.auth.auth_fingerprint import encrypt_data_with_fingerprint
from modules.auth.auth_jwt import create_jwt_token, set_jwt_cookie
from modules.crypto.operations.hybrid import decrypt
from shared_memory.shm_auth import add_auth_attempt_to_shm

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


async def auth_login_flow(
    request: Request, auth_data: EncryptedData, response: Response
) -> AuthResult:
    """
    Выполняет процесс авторизации пользователя с защитой от брутфорса

    :param request: объект запроса
    :param auth_data: зашифрованная строка логин:пароль
    :param response: объект ответа
    :return: результат авторизации (AuthResult)
    """
    client_ip = request.client.host
    now = int(time.time())

    locked_until = is_ip_locked(client_ip, now)
    if locked_until:
        return AuthResult(
            False,
            error_message=f"Слишком много попыток входа. Повторите через {locked_until - now} сек.",
        )

    decrypted_data = None
    try:
        decrypted_data = decrypt(auth_data.enc_data)
        username, password = decrypted_data.split(":", 1)
    except Exception as e:
        if decrypted_data:
            logger.warning(
                f"[{client_ip}] Invalid format of decrypted data: {decrypted_data}"
            )
        else:
            logger.error(
                f"[{client_ip}] Failed to decrypt authentication data: {str(e)}, error type: {type(e).__name__}"
            )
        if unlock_time := process_failed_attempt(client_ip, "<unknown>", now):
            return AuthResult(
                False,
                error_message=f"Слишком много попыток входа. Повторите через {unlock_time - now} сек.",
            )
        return AuthResult(
            False, error_message="Ошибка расшифровки или формата данных аутентификации"
        )

    credentials = HTTPBasicCredentials(username=username, password=password)
    validation = validate_credentials(credentials, client_ip)
    if validation.success:
        add_auth_attempt_to_shm(client_ip, username, now, success=True, unlock_time=0)
        data_fgp = {
            "username": username,
            "client_ip": client_ip,
            "current_time": now,
        }
        enc_data_fgp = encrypt_data_with_fingerprint(request.headers, data_fgp)
        token = create_jwt_token(
            username, client_ip=client_ip, enc_data_fgp=enc_data_fgp
        )
        set_jwt_cookie(response, token)
        logger.info(f"[{client_ip}][{username}] Successful authentication")
        return AuthResult(True, username=username)

    logger.warning(
        f"[{client_ip}][{username}] Authentication failed: {validation.error_message}"
    )
    if unlock_time := process_failed_attempt(client_ip, username, now):
        return AuthResult(
            False,
            error_message=f"Слишком много попыток входа. Повторите через {unlock_time - now} сек.",
        )
    return AuthResult(
        False, error_message=validation.error_message or "Неверные учетные данные"
    )
