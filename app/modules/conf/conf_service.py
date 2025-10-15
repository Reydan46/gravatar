import logging
import os
from typing import Any, Dict, Union

import yaml

from config.constants import LOG_CONFIG, CONFIG_FILE
from config.settings import settings
from modules.conf.conf_validator import (
    validate_ldap_options,
    validate_passphrase,
    validate_saml_options,
    validate_users,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

CONFIG_KEYS = {
    "passphrase": validate_passphrase,
    "users": validate_users,
    "ldap_options": validate_ldap_options,
    "saml_options": validate_saml_options,
}


def get_config_data_service() -> dict:
    """
    Возвращает текущие настройки конфигурации в виде словаря

    :return: Настройки из конфигурационного файла
    """
    try:
        return {key: getattr(settings, key) for key in CONFIG_KEYS}
    except Exception as e:
        logger.error(f"Failed to read {CONFIG_FILE}: {type(e).__name__}: {str(e)}")
        raise


def compose_update_data(
    current_settings: Dict[str, Any], update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Валидирует и собирает новые значения для всех ключей настроек

    :param current_settings: Действующие настройки
    :param update_data: Предложенные новые настройки
    :return: Новый словарь настроек после валидации и дополнения пропущенных значений
    """
    result = {}
    for key, validator in CONFIG_KEYS.items():
        if key in update_data:
            result[key] = validator(update_data[key])
        else:
            result[key] = current_settings.get(key)
    return result


def save_settings_to_file(settings_path: str, data: Dict[str, Any]) -> None:
    """
    Сохраняет настройки в файл CONFIG_FILE

    :param settings_path: Путь к CONFIG_FILE
    :param data: Словарь с данными для сохранения
    """
    sorted_data = {k: data[k] for k in sorted(data)}
    with open(settings_path, "w", encoding="utf-8") as f:
        yaml.dump(sorted_data, f, allow_unicode=True, sort_keys=False)
    if os.name != "nt":
        os.chmod(settings_path, 0o600)


async def update_config_service(update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обновляет настройки конфигурации атомарно (с валидацией), возвращает статус и разницу

    :param update_data: Словарь с новыми настройками
    :return: Словарь с success, error, diff и config
    """
    result: Dict[str, Union[bool, str, dict, None]] = {
        "success": False,
    }
    try:
        settings_path = os.path.join(settings.internal_data_path, CONFIG_FILE)
        current_settings = {key: getattr(settings, key) for key in CONFIG_KEYS}
        new_data = compose_update_data(current_settings, update_data)
        save_settings_to_file(settings_path, new_data)
        result["success"] = True
        logger.info(f"Updated config: {CONFIG_FILE}")
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Validation error in update_config_service: {error_msg}")
        result["error"] = error_msg
    except Exception as e:
        error_msg = (
            f"Failed to update config: {CONFIG_FILE}: {type(e).__name__}: {str(e)}"
        )
        logger.error(error_msg)
        result["error"] = error_msg
    return result


def validate_and_save_restored_config(
    file_contents: str,
) -> Dict[str, Union[bool, str]]:
    """
    Валидирует и сохраняет конфигурацию из файла восстановления

    :param file_contents: Содержимое файла settings.yml в виде строки
    :return: Словарь со статусом операции
    """
    result: Dict[str, Union[bool, str]] = {"success": False}
    try:
        restored_data = yaml.safe_load(file_contents)
        if not isinstance(restored_data, dict):
            raise ValueError("Restored config root must be a dictionary")

        for key in CONFIG_KEYS:
            if key not in restored_data:
                raise ValueError(f"Missing required key in configuration file: '{key}'")

        validated_data = {}
        for key, validator in CONFIG_KEYS.items():
            validated_data[key] = validator(restored_data[key])

        # Если всё прошло успешно, сохраняем
        settings_path = os.path.join(settings.internal_data_path, CONFIG_FILE)
        save_settings_to_file(settings_path, validated_data)
        result["success"] = True
        logger.info("Successfully restored and saved config from file")
    except (ValueError, yaml.YAMLError) as e:
        error_msg = str(e)
        logger.warning(f"Validation error during config restore: {error_msg}")
        result["error"] = error_msg
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = (
            f"Failed to restore config: {CONFIG_FILE}: {type(e).__name__}: {str(e)}"
        )
        logger.error(error_msg)
        result["error"] = error_msg
        raise IOError(error_msg)
    return result
