import logging

from filelock import FileLock, Timeout

from config.constants import LOG_CONFIG, SHARED_MEMORY_CONFIG
from shared_memory.shm_main import (
    get_shared_lock_path,
    shm_initialize,
    shm_read_int,
    shm_write_int,
    shm_cleanup,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["logs_counter"]

LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)


def initialize_logs_counter_shm(create: bool = True):
    """
    Инициализирует shared memory для счетчика логов

    :param create: Флаг, создавать ли новую shared memory
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], CONF["SIZE"], create)


def cleanup_logs_counter_shm(shm, is_creator: bool):
    """
    Очищает shared memory счетчика логов

    :param shm: Объект shared memory
    :param is_creator: Флаг, создан ли shm этим процессом
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def inc_logs_counter():
    """
    Инкрементирует счетчик логов в shared memory с блокировкой

    :return: Новое значение счетчика
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    shm, _ = initialize_logs_counter_shm(False)
    if shm is None:
        return
    try:
        with LOCK:
            buf = shm.buf
            value = shm_read_int(buf, 0)
            value = (value + 1) % CONF["MAX_VALUE"]
            shm_write_int(buf, 0, value)
    except Timeout:
        logger.error("Timeout acquiring lock for writing to logs counter shared memory")
        raise TimeoutError(
            "Timeout acquiring lock for writing to logs counter shared memory"
        )
    except Exception as e:
        logger.error(f"Error writing to logs counter shared memory: {e}")
        raise e


def get_logs_counter(shm) -> int:
    """
    Получает текущее значение счетчика логов из shared memory с блокировкой

    :param shm: объект shared memory
    :return: Текущее значение счетчика
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    if shm is None:
        return 0
    try:
        with LOCK:
            buf = shm.buf
            value = shm_read_int(buf, 0)
            return value
    except Timeout:
        logger.error(
            "Timeout acquiring lock for reading from logs counter shared memory"
        )
        raise TimeoutError(
            "Timeout acquiring lock for reading from logs counter shared memory"
        )
    except Exception as e:
        logger.error(f"Error reading from logs counter shared memory: {e}")
        raise e
