import logging
import re
from typing import Any, Dict, List

from config.constants import LOG_CONFIG
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

# Регулярное выражение для базовой проверки hostname/FQDN
HOSTNAME_REGEX = re.compile(
    r"^(?!-)(?!.*--)([a-zA-Z0-9-]{1,63})(?<!-)(\.(?!-)(?!.*--)([a-zA-Z0-9-]{1,63})(?<!-))*$"
)
# Регулярное выражение для строгой проверки Distinguished Name (DN) с разрешенными атрибутами
DN_REGEX = re.compile(
    r"^((?:CN|OU|DC|O|L|ST|C|UID)=[\w\s.-]+)(,(?:CN|OU|DC|O|L|ST|C|UID)=[\w\s.-]+)*$",
    re.IGNORECASE,
)
# Регулярное выражение для базовой проверки URL
URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


def validate_passphrase(passphrase: Any) -> str:
    """
    Валидирует основной пароль (passphrase) для доступа к API

    :param passphrase: Значение passphrase
    :return: Валидный passphrase
    :raises ValueError: Если значение некорректно
    """
    if not isinstance(passphrase, str) or not passphrase.strip():
        raise ValueError("passphrase должен быть непустой строкой")
    return passphrase.strip()


def validate_users(users: Any) -> List[Dict[str, Any]]:
    """
    Валидирует список пользователей (только уникальные username)

    :param users: Исходный список пользователей
    :return: Валидный список пользователей (уникальные username, правильные hash)
    """
    if not isinstance(users, list):
        raise ValueError("users должен быть списком")

    validated_users = []
    usernames = set()
    for user in users:
        if not isinstance(user, dict):
            logger.warning("Некорректная запись пользователя (не dict) пропущена")
            continue
        username = str(user.get("username", "")).strip()
        password_hash = str(user.get("password_hash", "")).strip()
        permissions = user.get("permissions", [])

        if not username or not password_hash:
            logger.warning(
                f"Пользователь с пустым username или password_hash пропущен: {username!r} {password_hash!r}"
            )
            continue
        if username in usernames:
            raise ValueError(f"Дублирующееся имя пользователя: {username!r}")
        usernames.add(username)
        validated_users.append(
            {
                "username": username,
                "password_hash": password_hash,
                "permissions": permissions if isinstance(permissions, list) else [],
            }
        )

    return validated_users


def validate_ldap_options(options: Any) -> Dict[str, str]:
    """
    Валидирует настройки подключения к LDAP.

    :param options: Словарь с настройками LDAP.
    :return: Валидированный словарь настроек.
    """
    if not isinstance(options, dict):
        raise ValueError("ldap_options должен быть словарем")

    default_options = settings.DEFAULT_SETTINGS["ldap_options"]
    validated_options = {}

    for key in default_options.keys():
        value = options.get(key)
        if value is None:
            validated_options[key] = ""
            continue

        if not isinstance(value, str):
            raise ValueError(f"Значение для '{key}' в ldap_options должно быть строкой")

        stripped_value = value.strip()

        if (
            key == "LDAP_SERVER"
            and stripped_value
            and not HOSTNAME_REGEX.match(stripped_value)
        ):
            raise ValueError(f"Некорректный формат сервера LDAP: '{stripped_value}'")

        if key == "LDAP_USERNAME" and not stripped_value:
            raise ValueError("Имя пользователя LDAP не может быть пустым")

        if (
            key == "LDAP_SEARCH_BASE"
            and stripped_value
            and not DN_REGEX.match(stripped_value)
        ):
            raise ValueError(
                f"Некорректный формат базы поиска LDAP: '{stripped_value}'"
            )

        validated_options[key] = stripped_value

    return validated_options


def validate_saml_options(options: Any) -> Dict[str, Any]:
    """
    Валидирует настройки SAML.

    :param options: Словарь с настройками SAML.
    :return: Валидированный словарь настроек.
    :raises ValueError: если какая-либо настройка некорректна.
    """
    if not isinstance(options, dict):
        raise ValueError("saml_options должен быть словарем.")

    # Проверка обязательных верхнеуровневых ключей
    required_keys = ["enabled", "sp", "idp", "security"]
    for key in required_keys:
        if key not in options:
            raise ValueError(f"Отсутствует обязательный ключ в saml_options: '{key}'")

    if not options.get("enabled"):
        return options  # Если выключено, дальнейшая валидация не нужна

    # Валидация IdP
    idp = options.get("idp", {})
    if not isinstance(idp.get("entityId"), str) or not idp["entityId"].strip():
        raise ValueError("saml_options.idp.entityId должен быть непустой строкой.")
    if not URL_REGEX.match(idp.get("singleSignOnService", {}).get("url", "")):
        raise ValueError(
            "Некорректный URL для saml_options.idp.singleSignOnService.url"
        )

    cert_idp = idp.get("x509cert", "")
    if not isinstance(cert_idp, str) or not cert_idp.strip():
        raise ValueError("Сертификат в saml_options.idp.x509cert не может быть пустым.")

    # Валидация SP
    sp = options.get("sp", {})
    if not URL_REGEX.match(sp.get("assertionConsumerService", {}).get("url", "")):
        raise ValueError(
            "Некорректный URL для saml_options.sp.assertionConsumerService.url"
        )

    security = options.get("security", {})
    sp_private_key = sp.get("privateKey", "").strip()
    sp_cert = sp.get("x509cert", "").strip()

    # Единая проверка для всех крипто-операций на стороне SP
    sp_crypto_required = any(
        [
            security.get("authnRequestsSigned"),
            security.get("logoutRequestSigned"),
            security.get("logoutResponseSigned"),
            security.get("signMetadata"),
            security.get("nameIdEncrypted"),
            security.get("wantAssertionsEncrypted"),
        ]
    )

    if sp_crypto_required and (not sp_private_key or not sp_cert):
        raise ValueError(
            "Приватный ключ и сертификат SP обязательны, если включена любая из опций подписи или шифрования."
        )

    return options
