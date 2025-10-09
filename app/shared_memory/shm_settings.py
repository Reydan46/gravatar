import json
import logging

from filelock import FileLock, Timeout

from config.constants import LOG_CONFIG, SHARED_MEMORY_CONFIG
from shared_memory.shm_main import (
    get_shared_lock_path,
    shm_initialize,
    shm_read_bytes,
    shm_read_int,
    shm_write_bytes,
    shm_write_int,
    shm_cleanup,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["settings"]

LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)


def initialize_settings_shm(create: bool = True):
    """
    Инициализирует shared memory для настроек

    :param create: True, если нужно создать shared memory
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(
        CONF["MEMORY_NAME"], CONF["HEADER_SIZE"] + CONF["SIZE"], create
    )


def cleanup_settings_shm(shm, is_creator: bool):
    """
    Очищает shared memory настроек

    :param shm: Объект shared memory
    :param is_creator: Флаг, создан ли shm этим процессом
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def write_settings_to_shm(mtime: int, data_dict: dict):
    """
    Записывает время и содержимое настроек в shared memory с блокировкой и таймаутом

    :param mtime: unixtime изменения файла
    :param data_dict: содержимое файла
    """
    shm, _ = initialize_settings_shm(False)
    if shm is None:
        return
    try:
        with LOCK:
            data_json = json.dumps(data_dict, ensure_ascii=False)
            data_bytes = data_json.encode("utf-8")
            if len(data_bytes) > CONF["SIZE"]:
                logger.error("Settings data is too big for shared memory")
                return
            shm_write_int(shm.buf, 0, int(mtime))
            shm_write_int(shm.buf, 8, len(data_bytes))
            shm_write_bytes(shm.buf, CONF["HEADER_SIZE"], data_bytes)
    except Timeout:
        logger.error("Timeout acquiring lock for writing to shared memory")
        raise TimeoutError("Timeout acquiring lock for writing to shared memory")
    except Exception as e:
        logger.error(f"Error writing to shared memory: {e}")
        raise e


def read_settings_from_shm() -> tuple[int, dict]:
    """
    Читает unixtime и содержимое (dict) настроек из shared memory с блокировкой и таймаутом

    :return: (mtime, dict)
    """
    shm, _ = initialize_settings_shm(False)
    if shm is None:
        return 0, {}
    try:
        with LOCK:
            mtime = shm_read_int(shm.buf, 0)
            size = shm_read_int(shm.buf, 8)
            if size > CONF["SIZE"] or size <= 0:
                return mtime, {}
            data_bytes = shm_read_bytes(shm.buf, CONF["HEADER_SIZE"], size)
            try:
                data = json.loads(data_bytes.decode("utf-8"))
            except Exception as e:
                logger.error(
                    f"Failed to decode settings from shm: {type(e).__name__}: {str(e)}"
                )
            return mtime, data
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e


def get_settings_field_from_shm(field_path: str):
    """
    Возвращает значение по dot-path из настроек, загруженных из shared memory

    :param field_path: Путь через точку к нужному полю
    :return: Значение поля или None
    """
    _, data = read_settings_from_shm()
    if not data:
        return None
    value = data
    for part in field_path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value
