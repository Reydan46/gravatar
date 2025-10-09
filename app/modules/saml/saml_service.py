import logging
import time
from typing import Dict, Optional

from fastapi import Request, Response
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from starlette.responses import HTMLResponse, RedirectResponse

from config.constants import (
    LOG_CONFIG,
    SAML_USER_PASSWORD_HASH_PLACEHOLDER,
    URL_PAGE_HOME,
)
from config.settings import settings
from modules.auth.auth_fingerprint import encrypt_data_with_fingerprint
from modules.auth.auth_jwt import create_jwt_token, set_jwt_cookie
from modules.saml.saml_utils import prepare_fastapi_request_for_saml

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class SAMLService:
    """
    Сервис для инкапсуляции логики SAML-аутентификации.
    """

    _instance: Optional["SAMLService"] = None
    _initialized: bool = False

    def __new__(cls) -> "SAMLService":
        if cls._instance is None:
            cls._instance = super(SAMLService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    @property
    def saml_settings(self) -> Dict:
        """
        Возвращает текущие настройки SAML.
        :return: Словарь с настройками SAML.
        """
        return settings.saml_options

    def is_enabled(self) -> bool:
        """
        Проверяет, включена ли SAML-аутентификация в настройках.
        :return: True, если SAML включен.
        """
        return self.saml_settings.get("enabled", False)

    async def get_auth_for_request(self, request: Request) -> OneLogin_Saml2_Auth:
        """
        Инициализирует и возвращает объект OneLogin_Saml2_Auth для текущего запроса.

        :param request: Объект запроса FastAPI.
        :return: Экземпляр OneLogin_Saml2_Auth.
        """
        req_data = await prepare_fastapi_request_for_saml(request)
        return OneLogin_Saml2_Auth(req_data, self.saml_settings)

    async def acs(self, request: Request, response: Response) -> HTMLResponse:
        """
        Обрабатывает Assertion Consumer Service (ACS) запрос.
        Выполняет JIT-провижининг, создает сессию пользователя и возвращает
        HTML-страницу с JavaScript-редиректом для корректной установки cookie.

        :param request: Объект запроса FastAPI.
        :param response: Объект ответа FastAPI для установки cookie.
        :return: Объект HTMLResponse со скриптом для редиректа.
        :raises ValueError: Если произошла ошибка при обработке SAML.
        """
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"[{client_ip}] Received SAML ACS request. Processing...")

        auth = await self.get_auth_for_request(request)

        # Получаем entityId IdP из настроек - это самый надежный способ
        idp_entity_id = (
            auth.get_settings().get_idp_data().get("entityId") or "unknown IdP"
        )

        auth.process_response()

        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            logger.error(
                f"[{client_ip}] SAML ACS Error from IdP '{idp_entity_id}': {errors}. Last reason: {error_reason}"
            )
            raise ValueError(f"SAML Error: {error_reason}")

        if not auth.is_authenticated():
            logger.warning(
                f"[{client_ip}] SAML ACS from IdP '{idp_entity_id}': Not authenticated."
            )
            raise ValueError("Not authenticated")

        name_id = auth.get_nameid()
        session_index = auth.get_session_index()

        if not name_id or not session_index:
            error_msg = f"NameID ({name_id}) or SessionIndex ({session_index}) not found in the SAML response."
            logger.error(
                f"[{client_ip}] SAML ACS from IdP '{idp_entity_id}': {error_msg}"
            )
            raise ValueError(error_msg)

        username = name_id.strip()
        logger.info(
            f"[{client_ip}][{username}] Successful SAML authentication from IdP '{idp_entity_id}'. NameID: {name_id}, SessionIndex: {session_index}"
        )

        # JIT Provisioning
        all_users = settings.users
        user_exists = any(u.get("username") == username for u in all_users)

        if not user_exists:
            logger.info(
                f"[{client_ip}][{username}] User not found. Provisioning a new SAML user."
            )
            new_user = {
                "username": username,
                "password_hash": SAML_USER_PASSWORD_HASH_PLACEHOLDER,
                "permissions": [],
            }
            all_users.append(new_user)
            settings.users = all_users
            logger.info(f"[{client_ip}][{username}] User successfully provisioned.")
        else:
            logger.info(f"[{client_ip}][{username}] SAML user found in the system.")

        # Создание JWT сессии
        data_fgp = {
            "username": username,
            "client_ip": client_ip,
            "current_time": int(time.time()),
        }
        enc_data_fgp = encrypt_data_with_fingerprint(request.headers, data_fgp)
        token = create_jwt_token(
            username,
            client_ip=client_ip,
            enc_data_fgp=enc_data_fgp,
            name_id=name_id,
            session_index=session_index,
        )
        set_jwt_cookie(response, token)

        relay_state = auth.get_last_request_id()
        redirect_url = URL_PAGE_HOME
        relay_state_source = "default"

        if relay_state and relay_state.startswith("/"):
            redirect_url = relay_state
            relay_state_source = "request_id"
        else:
            try:
                form_data = await request.form()
                relay_state_from_post = form_data.get("RelayState")
                if relay_state_from_post and relay_state_from_post.startswith("/"):
                    redirect_url = relay_state_from_post
                    relay_state_source = "form_body"
            except Exception:
                logger.warning(
                    f"[{client_ip}][{username}] Could not parse form data to get RelayState."
                )

        logger.info(
            f"[{client_ip}][{username}] Determined redirect URL: {redirect_url} (from {relay_state_source})."
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecting...</title>
            <script type="text/javascript">
                window.location.replace("{redirect_url}");
            </script>
        </head>
        <body>
            <p>Redirecting you to the application...</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, headers=response.headers)

    async def slo(self, request: Request) -> RedirectResponse:
        """
        Обрабатывает Single Log-Out (SLO) запрос от IdP.

        :param request: Объект запроса FastAPI.
        :return: Редирект на финальный эндпоинт очистки сессии.
        """
        client_ip = request.client.host if request.client else "unknown"
        auth = await self.get_auth_for_request(request)
        final_logout_url = "/auth/logout/final"

        # Получаем entityId IdP из настроек - это самый надежный способ
        idp_entity_id = (
            auth.get_settings().get_idp_data().get("entityId") or "unknown IdP"
        )

        auth.process_slo(delete_session_cb=lambda: None)
        errors = auth.get_errors()

        if errors:
            error_reason = auth.get_last_error_reason()
            logger.error(
                f"[{client_ip}] Error processing SAML SLS request from IdP '{idp_entity_id}': {errors}. Reason: {error_reason}"
            )
        else:
            logger.info(
                f"[{client_ip}] Processed SAML SLS request from IdP '{idp_entity_id}'. Redirecting to: {final_logout_url}"
            )

        return RedirectResponse(url=final_logout_url)


saml_service = SAMLService()
