import logging

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from config.constants import LOG_CONFIG
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

security_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
        credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> str:
    """
    Проверяет валидность API-ключа.

    :param credentials: Учетные данные из заголовка Authorization
    :return: Валидный API-ключ
    :raises HTTPException: Если API-ключ недействителен
    """
    if not credentials:
        logger.warning("Auth failed: no API key provided")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "You didn't provide an API key.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

    api_key = credentials.credentials

    if api_key != settings.passphrase:
        logger.warning(f"Auth failed: invalid API key '{api_key[:19]}...'")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Incorrect API key provided.",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

    logger.info(f"Auth successful: API key valid '{api_key[:19]}...'")
    return api_key
