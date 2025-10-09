import logging
from typing import Optional

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class AuthResult:
    """
    Результат аутентификации

    :param success: Успешна ли аутентификация
    :param username: Имя пользователя (если аутентификация успешна)
    :param error_message: Сообщение об ошибке (если аутентификация не успешна)
    """

    def __init__(
        self,
        success: bool,
        username: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.username = username
        self.error_message = error_message
