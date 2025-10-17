import hashlib
import logging
import os
import secrets
import string
import uuid
from typing import List, Optional, Union

from dotenv import dotenv_values

from config.constants import CONFIG_FILE, LOG_CONFIG, SECRET_FILE
from config.settings_descriptors import YamlSettingsDescriptorSHM
from utils.password_utils import check_password

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class Settings:
    """
    Глобальные настройки приложения

    :param -
    :return: None (Singleton)
    """

    _instance: Optional["Settings"] = None
    _initialized: bool = False
    _loaded_defaults = dotenv_values("/defaults.env") or {}

    DEFAULT_SETTINGS = {
        **{k.lower(): v for k, v in _loaded_defaults.items()},
        "passphrase": "",
        "users": [
            {
                "username": "admin",
                "password_hash": "$2b$12$umyahA293J3YQCaDRNezS.qBGAllHLoz64riz7aiER1BcXD0G/J8W",
                "permissions": ["logs", "settings", "gallery"],
            }
        ],
        "ldap_options": {
            "LDAP_SERVER": "",
            "LDAP_USERNAME": "",
            "LDAP_PASSWORD": "",
            "LDAP_SEARCH_BASE": "",
        },
        "saml_options": {
            "enabled": False,
            "debug": False,
            "strict": True,
            "sp": {
                "entityId": "https://example.com/saml/metadata",
                "assertionConsumerService": {
                    "url": "https://example.com/saml/acs",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": "https://example.com/saml/sls",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                "x509cert": "",
                "privateKey": "",
            },
            "idp": {
                "entityId": "https://example.com/realms/master",
                "singleSignOnService": {
                    "url": "https://example.com/realms/master/protocol/saml",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": "https://example.com/realms/master/protocol/saml",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": "MIICmzCCAYMCBgGMFhUQxjAN...BgkiG9w0BDBZMSU4f5LppuN5dvQfY=",
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": True,
                "wantAssertionsSigned": True,
                "wantAssertionsEncrypted": False,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            },
        },
    }

    def __new__(cls) -> "Settings":
        """
        Создает или возвращает существующий экземпляр класса (Singleton).
        """
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
        return cls._instance

    passphrase = YamlSettingsDescriptorSHM("passphrase", DEFAULT_SETTINGS["passphrase"])
    users = YamlSettingsDescriptorSHM("users", DEFAULT_SETTINGS["users"])
    ldap_options = YamlSettingsDescriptorSHM(
        "ldap_options", DEFAULT_SETTINGS["ldap_options"]
    )
    saml_options = YamlSettingsDescriptorSHM(
        "saml_options", DEFAULT_SETTINGS["saml_options"]
    )

    def __init__(self) -> None:
        """
        Инициализирует настройки приложения, загружая их из переменных окружения.
        """
        if Settings._initialized:
            return

        Settings._initialized = True
        self._app_host: str = os.getenv("APP_HOST", self.DEFAULT_SETTINGS["app_host"])
        self._app_port: str = os.getenv("APP_PORT", self.DEFAULT_SETTINGS["app_port"])
        self._nginx_port: str = os.getenv(
            "NGINX_PORT", self.DEFAULT_SETTINGS["nginx_port"]
        )
        self._app_workers: str = os.getenv(
            "APP_WORKERS", self.DEFAULT_SETTINGS["app_workers"]
        )
        self._app_reload: str = os.getenv(
            "APP_RELOAD", self.DEFAULT_SETTINGS["app_reload"]
        )
        self._internal_data_path: str = os.getenv(
            "INTERNAL_DATA_PATH", self.DEFAULT_SETTINGS["internal_data_path"]
        )
        self._show_debug_logs: str = os.getenv(
            "SHOW_DEBUG_LOGS", self.DEFAULT_SETTINGS["show_debug_logs"]
        )
        self._enable_root_redirect: str = os.getenv(
            "ENABLE_ROOT_REDIRECT", self.DEFAULT_SETTINGS["enable_root_redirect"]
        )
        self._jwt_secret_key: str = (
            os.getenv("JWT_SECRET_KEY") or self._get_or_create_secret_key()
        )
        self._jwt_algorithm: str = os.getenv(
            "JWT_ALGORITHM", self.DEFAULT_SETTINGS["jwt_algorithm"]
        )
        self._cors_allow_origins_raw: str = os.getenv(
            "CORS_ALLOW_ORIGINS", self.DEFAULT_SETTINGS["cors_allow_origins"]
        )
        self._allowed_hosts_raw: str = os.getenv(
            "ALLOWED_HOSTS", self.DEFAULT_SETTINGS["allowed_hosts"]
        )
        self._trusted_proxy_ips_raw: str = os.getenv(
            "TRUSTED_PROXY_IPS", self.DEFAULT_SETTINGS["trusted_proxy_ips"]
        )
        self._proxy_middleware_ignore_ips_raw: str = os.getenv(
            "PROXY_MIDDLEWARE_IGNORE_IPS",
            self.DEFAULT_SETTINGS["proxy_middleware_ignore_ips"],
        )

        self._initialize_passphrase()

    def _initialize_passphrase(self) -> None:
        """
        Проверяет наличие passphrase и генерирует новую, если она отсутствует.
        """
        current_passphrase = self.passphrase
        if not current_passphrase:
            logger.info("Passphrase not found or empty, generating a new one.")
            new_passphrase = self._generate_passphrase_string()
            self.passphrase = new_passphrase
            logger.info("New passphrase has been generated and saved.")

    @staticmethod
    def _generate_passphrase_string(length: int = 24) -> str:
        """
        Генерирует криптографически стойкую строку-пароль.

        :param length: Длина генерируемой строки.
        :return: Сгенерированная строка.
        """
        alphabet = string.ascii_letters + string.digits + "@!*-_^,."
        passphrase = "".join(secrets.choice(alphabet) for _ in range(length))
        logger.debug(f"Generated a new passphrase string of length {length}.")
        return passphrase

    def _get_or_create_secret_key(self) -> str:
        """
        Получает существующий секретный ключ из файла или создает новый

        :return: Строка с секретным ключом
        """
        secret_file_path = os.path.join(self.internal_data_path, SECRET_FILE)
        os.makedirs(self.internal_data_path, exist_ok=True)
        if os.path.exists(secret_file_path):
            try:
                with open(secret_file_path, "r") as f:
                    secret_key = f.read().strip()
                    if secret_key:
                        return secret_key
                    else:
                        logger.warning(
                            "JWT secret key file is empty. A new key will be generated."
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to read JWT secret key from file: {str(e)}. A new key will be generated."
                )

        logger.info("Generating new JWT secret key.")
        secret_key = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
        try:
            with open(secret_file_path, "w") as f:
                f.write(secret_key)
            if os.name != "nt":
                os.chmod(secret_file_path, 0o600)
            logger.info("Generated and saved new JWT secret key to file")
        except Exception as e:
            logger.error(
                f"Failed to save JWT secret key to file '{secret_file_path}': {str(e)}"
            )
        return secret_key

    def verify_password(self, username: str, password: str) -> bool:
        """
        Проверяет соответствие пароля для указанного пользователя

        :param username: Имя пользователя
        :param password: Пароль для проверки
        :return: True если пароль верный, False в противном случае
        """
        if not self.users:
            return False

        for user in self.users:
            if user.get("username") == username:
                return check_password(password, user.get("password_hash", ""))

        return False

    @property
    def trusted_proxy_ips_config(self) -> Union[List[str], str]:
        """
        Готовит конфигурацию для ProxyHeadersMiddleware на основе TRUSTED_PROXY_IPS

        - Если установлено "*": возвращает "*" (доверять всем).
        - Если установлено пустое значение: возвращает [] (не доверять никому).
        - Если задан список IP: возвращает этот список.

        :return: Конфигурация для trusted_hosts.
        """
        raw_value = self._trusted_proxy_ips_raw.strip()

        if raw_value == "*":
            return "*"

        if not raw_value:
            return []

        return [ip.strip() for ip in raw_value.split(",") if ip.strip()]

    @property
    def proxy_middleware_ignore_ips(self) -> List[str]:
        """
        Список IP-адресов, которые будут полностью проигнорированы Proxy Middleware
        Берется из переменной окружения PROXY_MIDDLEWARE_IGNORE_IPS

        :return: Список строк (IP-адресов).
        """
        raw_value = self._proxy_middleware_ignore_ips_raw.strip()
        if not raw_value:
            return []
        return [ip.strip() for ip in raw_value.split(",") if ip.strip()]

    @property
    def cors_allow_origins(self) -> List[str]:
        """
        Список разрешённых источников CORS из переменной окружения

        - Если установлено "*": возвращает ["*"] (разрешить все).
        - Если установлено пустое значение: возвращает [] (запретить все).
        - Если задан список: возвращает этот список.

        :return: Список строк (origins).
        """
        raw_value = self._cors_allow_origins_raw.strip()

        if raw_value == "*":
            return ["*"]

        if not raw_value:
            return []

        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> Union[List[str], str]:
        """
        Список разрешённых доменных имен (host) из переменной окружения ALLOWED_HOSTS

        - Если установлено "*": возвращает "*" (разрешить все).
        - Если установлено пустое значение: возвращает [] (запретить все).
        - Если задан список: возвращает этот список.

        :return: Список строк (хосты) или строка "*".
        """
        raw_value = self._allowed_hosts_raw.strip()

        if raw_value == "*":
            return "*"

        if not raw_value:
            return []

        return [h.strip().lower() for h in raw_value.split(",") if h.strip()]

    @property
    def app_host(self) -> str:
        """
        Хост для запуска приложения

        :return: Строка с хостом
        """
        return self._app_host

    @property
    def app_port(self) -> int:
        """
        Порт для запуска приложения

        :return: Целое число - порт
        """
        try:
            return int(self._app_port)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid APP_PORT value: '{self._app_port}'. Using default: {self.DEFAULT_SETTINGS['app_port']}"
            )
            return int(self.DEFAULT_SETTINGS["app_port"])

    @property
    def nginx_port(self) -> int:
        """
        Порт Nginx

        :return: Целое число - порт
        """
        try:
            return int(self._nginx_port)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid NGINX_PORT value: '{self._nginx_port}'. Using default: {self.DEFAULT_SETTINGS['nginx_port']}"
            )
            return int(self.DEFAULT_SETTINGS["nginx_port"])

    @property
    def app_workers(self) -> int:
        """
        Количество воркеров для запуска приложения

        :return: Целое число - количество воркеров
        """
        try:
            return int(self._app_workers)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid APP_WORKERS value: '{self._app_workers}'. Using default: {self.DEFAULT_SETTINGS['app_workers']}"
            )
            return int(self.DEFAULT_SETTINGS["app_workers"])

    @property
    def app_reload(self) -> bool:
        """
        Флаг перезагрузки приложения при изменении кода

        :return: Булево значение
        """
        if isinstance(self._app_reload, bool):
            return self._app_reload

        return str(self._app_reload).lower() in ("true", "t", "yes", "y", "1")

    @property
    def internal_data_path(self) -> str:
        """
        Путь к внутренним данным приложения

        :return: Строка с путем
        """
        return self._internal_data_path

    @property
    def show_debug_logs(self) -> bool:
        """
        Флаг для отображения отладочных сообщений логирования

        :return: Булево значение
        """
        if isinstance(self._show_debug_logs, bool):
            return self._show_debug_logs

        return str(self._show_debug_logs).lower() in ("true", "t", "yes", "y", "1")

    @property
    def enable_root_redirect(self) -> bool:
        """
        Флаг, включающий перенаправление с корневого URL на домашнюю страницу.

        :return: Булево значение.
        """
        if isinstance(self._enable_root_redirect, bool):
            return self._enable_root_redirect
        return str(self._enable_root_redirect).lower() in ("true", "t", "yes", "y", "1")

    @property
    def jwt_secret_key(self) -> str:
        """
        Секретный ключ для JWT токенов

        :return: Строка с секретным ключом
        """
        return self._jwt_secret_key

    @property
    def jwt_algorithm(self) -> str:
        """
        Алгоритм для JWT токенов

        :return: Строка с названием алгоритма
        """
        return self._jwt_algorithm

    @property
    def last_settings_edit_time(self) -> int:
        """
        Время последнего редактирования settings.yml в формате Unix timestamp (int)

        :return: Unixtime изменения файла (int), 0 если файл не найден
        """
        settings_path = os.path.join(self.internal_data_path, CONFIG_FILE)
        try:
            return int(os.path.getmtime(settings_path))
        except Exception as e:
            logger.warning(f"Failed to get last settings edit time: {str(e)}")
            return 0


settings = Settings()
