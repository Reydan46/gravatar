import logging
import struct

from filelock import FileLock, Timeout

from config.constants import LOG_CONFIG, SHARED_MEMORY_CONFIG
from shared_memory.shm_logs_counter import inc_logs_counter
from shared_memory.shm_main import (
    get_shared_lock_path,
    shm_initialize,
    shm_read_bytes,
    shm_read_int,
    shm_write_bytes,
    shm_write_int,
    _shorten_message,
    shm_cleanup,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["logs"]
LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)

STRUCT_FORMAT = "".join(
    f'{CONF["ENTRY_SIZES"][entry]}s' for entry in CONF["ENTRY_ORDER"]
)
ENTRY_STRUCT = struct.Struct(STRUCT_FORMAT)
ENTRY_SIZE = ENTRY_STRUCT.size
TOTAL_SIZE = CONF["HEADER_SIZE"] + CONF["MAX_BUFFER_SIZE"] * (
    CONF["ENTRY_HEADER_SIZE"] + ENTRY_SIZE
)


def initialize_logs_shm(create: bool = True, enable_logging: bool = True):
    """
    Инициализирует shared memory для логов

    :param create: Флаг, создавать ли новую память
    :param enable_logging: Включает или отключает логирование в shm_initialize
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], TOTAL_SIZE, create, enable_logging)


def cleanup_logs_shm(shm, is_creator: bool):
    """
    Очищает shared memory

    :param shm: Объект shared memory
    :param is_creator: Флаг, создан ли shm этим процессом
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def _pack_log_entry(log_entry: dict) -> bytes:
    """
    Упаковывает запись лога в бинарный формат

    :param log_entry: Словарь с данными лога
    :return: Упакованные байты
    """
    packed_entries = []
    for entry in CONF["ENTRY_ORDER"]:
        value: str = str(log_entry.get(entry, ""))
        if entry == "message":
            value = _shorten_message(value, CONF["ENTRY_SIZES"]["message"])
        data = value.encode("utf-8")[: CONF["ENTRY_SIZES"][entry]]
        if len(data) < CONF["ENTRY_SIZES"][entry]:
            data += b" " * (CONF["ENTRY_SIZES"][entry] - len(data))
        packed_entries.append(data)
    return ENTRY_STRUCT.pack(*packed_entries)


def add_log_to_shm(log_entry: dict):
    """
    Добавляет запись лога в shared memory с блокировкой и обработкой таймаута

    :param log_entry: Словарь с данными лога
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    shm, _ = initialize_logs_shm(False, enable_logging=False)
    if not shm or shm.buf is None:
        return
    packed = _pack_log_entry(log_entry)
    entry_full_size = CONF["ENTRY_HEADER_SIZE"] + ENTRY_SIZE
    try:
        with LOCK:
            inc_logs_counter()

            buf = shm.buf
            count = shm_read_int(buf, 0)
            next_idx = shm_read_int(buf, 4)
            offset = CONF["HEADER_SIZE"] + (next_idx * entry_full_size)
            shm_write_int(buf, offset, ENTRY_SIZE)
            shm_write_bytes(buf, offset + CONF["ENTRY_HEADER_SIZE"], packed)
            next_idx = (next_idx + 1) % CONF["MAX_BUFFER_SIZE"]
            count = min(count + 1, CONF["MAX_BUFFER_SIZE"])
            shm_write_int(buf, 0, count)
            shm_write_int(buf, 4, next_idx)
    except Timeout:
        logger.error("Timeout acquiring lock for writing to shared memory")
        raise TimeoutError("Timeout acquiring lock for writing to shared memory")
    except Exception as e:
        logger.error(f"Error writing to shared memory: {e}")


def get_logs_from_shm(limit: int = 1000) -> list:
    """
    Получает последние записи логов из shared memory с блокировкой и обработкой таймаута

    :param limit: Максимальное количество записей
    :return: Список записей логов
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    shm, _ = initialize_logs_shm(False, enable_logging=False)
    if not shm or shm.buf is None:
        return []
    try:
        with LOCK:
            buf = shm.buf
            count = shm_read_int(buf, 0)
            next_idx = shm_read_int(buf, 4)
            num_logs = min(int(count), int(limit))
            if num_logs == 0:
                return []

            start_idx = (next_idx - num_logs) % CONF["MAX_BUFFER_SIZE"]
            entry_full_size = CONF["ENTRY_HEADER_SIZE"] + ENTRY_SIZE

            logs = []
            for i in range(num_logs):
                idx = (start_idx + i) % CONF["MAX_BUFFER_SIZE"]
                offset = CONF["HEADER_SIZE"] + (idx * entry_full_size)
                data_size = shm_read_int(buf, offset)
                if data_size != ENTRY_SIZE:
                    continue
                packed = shm_read_bytes(
                    buf, offset + CONF["ENTRY_HEADER_SIZE"], ENTRY_SIZE
                )
                unpacked = ENTRY_STRUCT.unpack(packed)
                logs.append(
                    {
                        entry: unpacked[j].decode("utf-8", "ignore").rstrip(" ")
                        for j, entry in enumerate(CONF["ENTRY_ORDER"])
                    }
                )
            return logs
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e
