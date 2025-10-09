import asyncio
import logging
import os
import time

from filelock import FileLock, Timeout

from config.constants import SHARED_MEMORY_CONFIG, LOG_CONFIG
from config.settings import settings
from shared_memory.shm_main import (
    shm_initialize,
    shm_write_int,
    shm_read_int,
    get_shared_lock_path,
    shm_cleanup,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["pids"]

LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)


def initialize_pids_shm(create: bool = True):
    """
    Инициализирует shared memory для PIDs

    :param create: True, если shared memory должен быть создан
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], CONF["SIZE"], create)


def cleanup_pids_shm(shm, is_creator: bool):
    """
    Очищает shared memory PIDs

    :param shm: Объект shared memory
    :param is_creator: Флаг, создан ли shm этим процессом
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def register_pid(shm) -> int:
    """
    Записывает PID текущего процесса в shared memory и возвращает новое количество.

    :param shm: объект shared memory
    :return: Новое общее количество зарегистрированных PID'ов
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    try:
        with LOCK:
            idx = shm_read_int(shm.buf, 0)
            shm_write_int(shm.buf, (idx + 1) * 4, os.getpid())
            new_count = idx + 1
            shm_write_int(shm.buf, 0, new_count)
            return new_count
    except Timeout:
        logger.error("Timeout acquiring lock for writing to shared memory")
        raise TimeoutError("Timeout acquiring lock for writing to shared memory")
    except Exception as e:
        logger.error(f"Error writing to shared memory: {e}")
        raise e


def get_all_pids(shm) -> list[int]:
    """
    Возвращает список всех PID из shared memory с блокировкой и удалением lock-файла

    :param shm: объект shared memory
    :return: список PID
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    try:
        with LOCK:
            count = shm_read_int(shm.buf, 0)
            return [shm_read_int(shm.buf, i) for i in range(4, (count + 1) * 4, 4)]
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e


async def log_pids(shm, timeout: float = 10.0):
    """
    Эмулирует барьер, ожидая регистрации всех воркеров, после чего "лидер" логирует PIDы.

    :param shm: объект shared memory
    :param timeout: Максимальное время ожидания в секундах
    """
    total_workers = settings.app_workers
    my_pid = os.getpid()

    register_pid(shm)

    start_time = time.monotonic()
    while True:
        all_pids = get_all_pids(shm)
        if len(all_pids) >= total_workers:
            break
        if time.monotonic() - start_time > timeout:
            logger.warning(
                f"PID barrier timeout: expected {total_workers}, but only {len(all_pids)} registered. "
                f"PIDs: {all_pids}"
            )
            break
        await asyncio.sleep(0.05)

    is_leader = bool(all_pids and my_pid == min(all_pids))

    if is_leader:
        logger.info(
            f"Server is running on {len(all_pids)} processes: {', '.join(map(str, sorted(all_pids)))}"
        )
