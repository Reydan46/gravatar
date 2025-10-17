import json
import logging
import os

import yaml
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from starlette.responses import FileResponse, RedirectResponse
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)

from api.crypto.crypto_schema import HybridEncryptedData, EncryptedSymmetricKey
from config.constants import LOG_CONFIG, CONFIG_FILE
from config.settings import settings
from modules.auth.auth_jwt import validate_jwt
from modules.auth.auth_permissions import require_permission, Permissions
from modules.conf.conf_service import (
    get_config_data_service,
    update_config_service,
    validate_and_save_restored_config,
)
from modules.crypto.operations.hybrid import encrypt_hybrid, decrypt_hybrid
from utils.request_logging import log_request_error

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

conf_router = APIRouter(prefix="/conf", tags=["Conf"])


@conf_router.get("", response_class=HTMLResponse)
async def config_page(request: Request, response: Response):
    """
    Возвращает HTML-страницу настройки конфигурации приложения

    Предоставляет интерфейс для изменения параметров конфигурации через браузер
    Проверяет авторизацию пользователя перед отображением страницы

    :param request: HTTP-запрос для анализа сессии
    :param response: HTTP-ответ, используется для проверки авторизации
    :return: HTML-страница конфигурации
    """
    try:
        await validate_jwt(request, response, auto_refresh=False)
        return FileResponse("static/conf.html", media_type="text/html")
    except HTTPException:
        return RedirectResponse(
            url=f"/auth?next=/conf", status_code=HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Config page error"
        )


@conf_router.post("/data")
async def get_config_data(
    request: Request, response: Response, enc_payload: EncryptedSymmetricKey
):
    """
    Возвращает текущие параметры конфигурации приложения в формате JSON

    Используется для просмотра текущих настроек через защищенный интерфейс
    Требует наличие соответствующих прав доступа у пользователя

    :param request: HTTP-запрос сессии пользователя
    :param enc_payload: Зашифрованные данные конфигурации (AES+RSA)
    :param response: HTTP-ответ для контроля авторизации
    :return: Текущий конфиг приложения в виде JSON-объекта
    """
    try:
        username, _ = await validate_jwt(request, response)
        require_permission(username, Permissions.SETTINGS)
        data_string = json.dumps(get_config_data_service())
        return encrypt_hybrid(enc_payload.model_dump(exclude_unset=True), data_string)
    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Config data error"
        )


@conf_router.post("/update")
async def update_config(
    request: Request, response: Response, payload: HybridEncryptedData
):
    """
    Обновляет параметры конфигурации приложения на новые значения

    Принимает обновленные значения, валидирует и применяет их атомарно в системе
    Доступно только пользователям с соответствующими правами

    :param request: HTTP-запрос с новыми данными конфигурации
    :param payload: Зашифрованные данные конфигурации (AES+RSA)
    :param response: HTTP-ответ для проверки прав
    :return: Статус
    """
    try:
        username, _ = await validate_jwt(request, response)
        require_permission(username, Permissions.SETTINGS)
        try:
            update_data_str = decrypt_hybrid(payload.model_dump(exclude_unset=True))
        except ValueError:
            logger.warning(
                f"Decryption failed for user '{username}'. Keys may be outdated. Sending 409 Conflict."
            )
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Decryption failed. Client keys may be outdated.",
            )
        update_data = json.loads(update_data_str)
        logger.info(f"[{username}] Request to update config")
        return await update_config_service(update_data)
    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Config update error"
        )


@conf_router.post("/backup")
async def download_backup(
    request: Request, response: Response, enc_payload: EncryptedSymmetricKey
):
    """
    Отдаёт зашифрованное содержимое файла settings.yml

    :param request: HTTP-запрос
    :param response: HTTP-ответ
    :param enc_payload: Зашифрованный AES-ключ от клиента
    :return: Зашифрованное содержимое файла settings.yml
    """
    try:
        username, _ = await validate_jwt(request, response)
        require_permission(username, Permissions.SETTINGS)
        logger.info(f"[{username}] Request to download config backup")
        settings_path = os.path.join(settings.internal_data_path, CONFIG_FILE)
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
        return encrypt_hybrid(enc_payload.model_dump(exclude_unset=True), content)
    except HTTPException:
        raise
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Backup config error"
        )


@conf_router.post("/restore")
async def upload_restore(
    request: Request, response: Response, payload: HybridEncryptedData
):
    """
    Принимает зашифрованный файл settings.yml, валидирует и восстанавливает конфигурацию

    :param request: HTTP-запрос
    :param response: HTTP-ответ
    :param payload: Зашифрованное содержимое файла
    :return: Статус операции
    """
    try:
        username, _ = await validate_jwt(request, response)
        require_permission(username, Permissions.SETTINGS)
        logger.info(f"[{username}] Request to restore config from file")

        try:
            decrypted_contents = decrypt_hybrid(payload.model_dump(exclude_unset=True))
        except ValueError:
            logger.warning(
                f"Decryption failed for user '{username}'. Keys may be outdated. Sending 409 Conflict."
            )
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Decryption failed. Client keys may be outdated.",
            )
        return validate_and_save_restored_config(decrypted_contents)
    except HTTPException:
        raise
    except yaml.YAMLError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Invalid YAML file format"
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log_request_error(request, e)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Restore config error"
        )
