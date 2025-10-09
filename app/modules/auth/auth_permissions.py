import logging
from enum import Enum

from fastapi import HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from config.constants import LOG_CONFIG
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

class Permissions(str, Enum):
    LOGS = "logs"
    SETTINGS = "settings"
    GALLERY = "gallery"

def has_permission(username: str, permission: str) -> bool:
    """
    Проверяет наличие разрешения у пользователя

    :param username: Имя пользователя
    :param permission: Проверяемое разрешение
    :return: True если разрешение присутствует
    """
    user = next((u for u in settings.users if u.get("username") == username), None)
    if user:
        permissions = user.get("permissions", [])
        return permission in permissions
    return False


def require_permission(username: str, permission: Permissions) -> None:
    """
    Проверяет наличие разрешения у пользователя и выбрасывает HTTPException 403 при отсутствии

    :param username: Имя пользователя
    :param permission: Требуемое разрешение
    :raises HTTPException: Если доступа недостаточно
    """
    if not has_permission(username, permission.value):
        logger.warning(
            f"Access denied for user '{username}': missing permission '{permission}'"
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Access denied: permission '{permission}' required",
        )
