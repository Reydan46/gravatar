import logging

from fastapi import APIRouter, HTTPException, Request, Response
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from api.crypto.crypto_schema import (
    EncryptedData,
    PrivateKeyRequest,
)
from config.constants import LOG_CONFIG
from modules.auth.auth_jwt import validate_jwt
from modules.crypto.operations.hybrid import decrypt
from modules.crypto.crypto_service import (
    get_public_key_jwk,
    generate_private_key,
    generate_cert_from_key,
)
from utils.password_utils import generate_password_hash
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

crypto_router = APIRouter(prefix="/crypto", tags=["Crypto"])


@crypto_router.post("/public_key")
async def get_public_key(request: Request):
    """
    Возвращает публичный ключ RSA для шифрования учетных данных пользователей на клиенте

    Используется для криптографической защиты паролей при передаче на сервер
    Помогает обеспечить безопасную аутентификацию через открытый канал связи

    :return: Публичный ключ в формате JSON Web Key
    """
    try:
        return get_public_key_jwk()
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Public key generation error",
        )


@crypto_router.post("/hash_password")
async def get_password_hash(
    request: Request, response: Response, password_data: EncryptedData
):
    """
    Генерирует безопасный хеш для переданного пароля (принимает зашифрованные данные)

    :param request: HTTP-запрос с зашифрованным паролем
    :param response: HTTP-ответ, необходим для проверки авторизации пользователя
    :param password_data: Зашифрованный пароль для получения хэша
    :return: Хеш пароля в защищенном формате
    """
    try:
        await validate_jwt(request, response)
        password = decrypt(password_data.enc_data)
        return {"hash": generate_password_hash(password or "")}
    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password hash generation error",
        )


@crypto_router.post("/generate_private_key")
async def generate_new_private_key(request: Request, response: Response):
    """
    Генерирует новый приватный ключ RSA 2048 бит.

    :param request: HTTP-запрос
    :param response: HTTP-ответ
    :return: Словарь с приватным ключом в формате PEM (однострочный Base64).
    """
    try:
        await validate_jwt(request, response)
        logger.info("Request to generate new private key.")
        private_key_pem_oneline = generate_private_key()
        return {"private_key": private_key_pem_oneline}
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Private key generation error",
        )


@crypto_router.post("/generate_cert_from_key")
async def generate_certificate_from_key(
    request: Request, response: Response, key_data: PrivateKeyRequest
):
    """
    Генерирует самоподписанный сертификат на основе переданного приватного ключа.

    :param request: HTTP-запрос
    :param response: HTTP-ответ
    :param key_data: Данные с приватным ключом.
    :return: Словарь с сертификатом в формате PEM (однострочный Base64).
    """
    try:
        await validate_jwt(request, response)
        logger.info("Request to generate certificate from existing private key.")
        cert_pem_oneline = generate_cert_from_key(key_data.private_key)
        return {"certificate": cert_pem_oneline}
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate generation error",
        )
