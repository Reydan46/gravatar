import logging

from filelock import FileLock, Timeout

from config.constants import SHARED_MEMORY_CONFIG, LOG_CONFIG
from shared_memory.shm_main import (
    shm_initialize,
    shm_write_int,
    shm_read_int,
    get_shared_lock_path,
    shm_cleanup,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["shutdown"]

LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)


def initialize_shutdown_shm(create: bool = True):
    """
    Инициализирует shared memory для shutdown IPC

    :param create: флаг создания shared memory
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], CONF["SIZE"], create)


def cleanup_shutdown_shm(shm, is_creator: bool):
    """
    Очищает shared memory shutdown

    :param shm: Объект shared memory
    :param is_creator: Флаг, создан ли shm этим процессом
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def set_shutdown_flag(shm, value: bool = True):
    """
    Устанавливает флаг shutdown в shared memory с блокировкой и удалением lock-файла

    :param shm: объект shared memory
    :param value: значение признака выключения (0 или 1)
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    try:
        with LOCK:
            shm_write_int(shm.buf, 0, int(value))
    except Timeout:
        logger.error("Timeout acquiring lock for writing to shared memory")
        raise TimeoutError("Timeout acquiring lock for writing to shared memory")
    except Exception as e:
        logger.error(f"Error writing to shared memory: {e}")
        raise e


def get_shutdown_flag(shm) -> int:
    """
    Получает значение флага shutdown из shared memory с блокировкой и удалением lock-файла

    :param shm: объект shared memory
    :return: 0 или 1
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    try:
        with LOCK:
            return shm_read_int(shm.buf, 0)
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e
