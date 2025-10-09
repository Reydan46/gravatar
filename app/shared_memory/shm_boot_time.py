import logging

from filelock import FileLock, Timeout

from config.constants import SHARED_MEMORY_CONFIG, LOG_CONFIG
from shared_memory.shm_main import (
    shm_initialize,
    shm_cleanup,
    shm_write_float,
    shm_read_float,
    get_shared_lock_path,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["boot_time"]

LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)


def initialize_boot_time_shm(create: bool = True):
    """
    Инициализирует shared memory для boot_time (float timestamp)

    :param create: Флаг создания shared memory
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], CONF["SIZE"], create)


def cleanup_boot_time_shm(shm, is_creator: bool):
    """
    Очищает shared memory boot_time

    :param shm: Объект shared memory
    :param is_creator: Флаг, создан ли shm этим процессом
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def set_boot_time(shm, timestamp: float):
    """
    Устанавливает float unixtime boot_time в shared memory с блокировкой

    :param shm: объект shared memory
    :param timestamp: unixtime (float)
    """
    try:
        with LOCK:
            shm_write_float(shm.buf, 0, float(timestamp))
    except Timeout:
        logger.error("Timeout acquiring lock for writing to shared memory")
        raise TimeoutError("Timeout acquiring lock for writing to shared memory")
    except Exception as e:
        logger.error(f"Error writing to shared memory: {e}")
        raise e


def get_boot_time() -> float:
    """
    Получает float unixtime boot_time из shared memory с блокировкой

    :return: unixtime (float)
    """
    shm, _ = initialize_boot_time_shm(False)
    if shm is None:
        return 0
    try:
        with LOCK:
            return shm_read_float(shm.buf, 0)
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e
