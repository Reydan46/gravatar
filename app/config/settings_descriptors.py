import logging
import os
from copy import deepcopy
from typing import Any, Dict

import yaml
from filelock import FileLock

from config.constants import CONFIG_FILE, LOG_CONFIG
from shared_memory.shm_settings import read_settings_from_shm, write_settings_to_shm
from utils.dict_utils import deep_merge_dicts

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


class YamlSettingsDescriptorSHM:
    """
    Дескриптор для автосинхронизации настроек из YAML через shared_memory

    :param setting_key: путь до ключа (через точку)
    :param default_value: значение по умолчанию
    """

    def __init__(self, setting_key: str, default_value: Any):
        self._key = setting_key
        self._default = default_value

    @staticmethod
    def _merge_with_defaults(
            instance: Any, file_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Сливает данные из файла с дефолтными настройками, создавая полный объект конфигурации.

        :param instance: Экземпляр класса Settings для доступа к DEFAULT_SETTINGS.
        :param file_data: Данные, прочитанные из settings.yml.
        :return: Полный словарь настроек со всеми значениями.
        """
        all_settings_with_defaults = {}
        for key, default in instance.DEFAULT_SETTINGS.items():
            if isinstance(default, dict):
                merged_value = deepcopy(default)
                if key in file_data and isinstance(file_data[key], dict):
                    deep_merge_dicts(file_data[key], merged_value)
                all_settings_with_defaults[key] = merged_value
            else:
                all_settings_with_defaults[key] = file_data.get(key, default)
        return all_settings_with_defaults

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        path = os.path.join(instance.internal_data_path, CONFIG_FILE)
        try:
            file_mtime = int(os.path.getmtime(path))
        except FileNotFoundError:
            logger.info(f"Settings file not found at {path}, using defaults.")
            default_config = self._merge_with_defaults(instance, {})
            write_settings_to_shm(0, default_config)
            return default_config.get(self._key, self._default)
        except Exception as e:
            logger.warning(
                f"Cannot access settings file at {path}: {type(e).__name__}: {str(e)}"
            )
            return self._default

        shm_mtime, shm_data = read_settings_from_shm()

        if shm_mtime != file_mtime or not shm_data:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_data = yaml.safe_load(f) or {}

                all_settings_with_defaults = self._merge_with_defaults(
                    instance, file_data
                )
                write_settings_to_shm(file_mtime, all_settings_with_defaults)
                shm_data = all_settings_with_defaults

            except Exception as e:
                logger.error(
                    f"Failed to parse {CONFIG_FILE}: {type(e).__name__}: {str(e)}"
                )
                return self._default

        return shm_data.get(self._key, self._default)

    def __set__(self, instance, value: Any) -> None:
        """
        Устанавливает значение в YAML файл и обновляет shared memory.

        :param instance: экземпляр класса Settings
        :param value: новое значение для установки
        :return: None
        """
        if instance is None:
            return

        path = os.path.join(instance.internal_data_path, CONFIG_FILE)
        lock_path = f"{path}.lock"
        file_lock = FileLock(lock_path, timeout=2)

        try:
            with file_lock:
                # Читаем текущие данные из файла
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                except FileNotFoundError:
                    logger.info(f"Creating new settings file at {path}")
                    data = {}

                current = data
                keys = self._key.split(".")
                for k in keys[:-1]:
                    current = current.setdefault(k, {})
                current[keys[-1]] = value

                # Записываем обратно в файл
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                if os.name != "nt":
                    os.chmod(path, 0o600)

                # Обновляем shared memory
                file_mtime = int(os.path.getmtime(path))

                all_settings_with_defaults = self._merge_with_defaults(instance, data)
                write_settings_to_shm(file_mtime, all_settings_with_defaults)

        except Exception as e:
            logger.error(
                f"Failed to write {CONFIG_FILE} or update SHM: {type(e).__name__}: {str(e)}"
            )
            raise
