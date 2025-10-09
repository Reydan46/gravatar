import logging
from fastapi.security import HTTPBasicCredentials

from config.constants import LOG_CONFIG
from config.settings import settings
from modules.auth.auth_base import AuthResult

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def validate_credentials(
    credentials: HTTPBasicCredentials, client_ip: str
) -> AuthResult:
    """
    Проверяет учетные данные пользователя по установленным настройкам

    :param credentials: Объект с учетными данными пользователя
    :param client_ip: IP-адрес клиента
    :return: Результат аутентификации
    """
    if not credentials:
        logger.warning(
            f"[{client_ip}] Unauthorized access attempt: missing credentials"
        )
        return AuthResult(False, error_message="Не переданы учетные данные")

    try:
        # Логируем попытку аутентификации
        logger.debug(f"[{client_ip}][{credentials.username}] Validating credentials")

        # Проверяем наличие пользователя в списке users
        user_exists = any(
            user.get("username") == credentials.username for user in settings.users
        )
        if not user_exists:
            logger.debug(
                f"[{client_ip}][{credentials.username}] User not found in users list"
            )
            return AuthResult(False, error_message="Неверные учетные данные")

        is_valid = settings.verify_password(credentials.username, credentials.password)

        if not is_valid:
            logger.debug(
                f"[{client_ip}][{credentials.username}] Invalid password for user '{credentials.username}'"
            )
            return AuthResult(False, error_message="Неверные учетные данные")

        return AuthResult(True, username=credentials.username)
    except Exception as e:
        logger.error(
            f"[{client_ip}][{credentials.username}] Authentication error: {str(e)}, type: {type(e).__name__}"
        )
        return AuthResult(False, error_message=f"Системная ошибка")
