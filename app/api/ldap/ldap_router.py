import logging

import orjson
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from api.ldap.ldap_schema import LdapCheckRequest, LdapCheckResponse
from config.constants import LOG_CONFIG
from modules.auth.auth_jwt import validate_jwt
from modules.auth.auth_permissions import Permissions, require_permission
from modules.crypto.operations.hybrid import decrypt_hybrid
from modules.ldap.ldap_service import check_connection_from_credentials
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

ldap_router = APIRouter(prefix="/ldap", tags=["LDAP"])


@ldap_router.post("/check", response_model=LdapCheckResponse)
async def check_ldap_connection(
    request: Request, response: Response, payload: LdapCheckRequest
):
    """
    Проверяет соединение с LDAP сервером, используя переданные учетные данные.

    :param request: HTTP-запрос.
    :param response: HTTP-ответ.
    :param payload: Зашифрованные учетные данные LDAP.
    :return: Результат проверки соединения.
    """

    try:
        username, _ = await validate_jwt(request, response)
        require_permission(username, Permissions.SETTINGS)
        logger.info(f"[{username}] Received LDAP connection check request.")

        decrypted_str = decrypt_hybrid(payload.model_dump(exclude_unset=True))
        ldap_data = orjson.loads(decrypted_str)

        result = check_connection_from_credentials(ldap_data)
        return {"success": result.success, "message": result.message}

    except ValueError as e:
        logger.warning(f"LDAP check failed due to bad request: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except orjson.JSONDecodeError:
        logger.warning(f"LDAP check failed due to invalid JSON in payload.")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid data format"
        )
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during LDAP connection check.",
        )
