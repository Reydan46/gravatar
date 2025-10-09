import logging
import struct

from filelock import FileLock, Timeout

from config.constants import LOG_CONFIG, SHARED_MEMORY_CONFIG
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
CONF = SHARED_MEMORY_CONFIG["auth"]

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


def initialize_auth_shm(create: bool = True):
    """
    Инициализирует shared memory для попыток авторизации

    :param create: Создавать ли новый сегмент
    :return: Кортеж (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], TOTAL_SIZE, create)


def cleanup_auth_shm(shm, is_creator: bool):
    """
    Очищает shared memory

    :param shm: Объект shared memory
    :param is_creator: Логический флаг создателя shm
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def _pack_attempt_entry(
    client_ip: str, timestamp: int, username: str, success: bool, unlock_time: int
) -> bytes:
    """
    Упаковывает одну неудачную попытку входа

    :param client_ip: IP-адрес
    :param timestamp: Время попытки (unixtime)
    :param username: Имя пользователя
    :param success: Флаг успешности попытки (True/False)
    :param unlock_time: Время разблокировки, если установлен бан (иначе 0)
    :return: Упакованный entry
    """
    values = []
    for entry in CONF["ENTRY_ORDER"]:
        if entry == "ip":
            value = client_ip
        elif entry == "timestamp":
            value = str(timestamp)
        elif entry == "username":
            value = _shorten_message(username, CONF["ENTRY_SIZES"]["username"], "")
        elif entry == "success":
            value = "1" if success else "0"
        elif entry == "unlock_time":
            value = str(unlock_time)
        else:
            value = ""
        data = value.encode("utf-8")[: CONF["ENTRY_SIZES"][entry]]
        if len(data) < CONF["ENTRY_SIZES"][entry]:
            data += b" " * (CONF["ENTRY_SIZES"][entry] - len(data))
        values.append(data)
    return ENTRY_STRUCT.pack(*values)


def add_auth_attempt_to_shm(
    client_ip: str, username: str, timestamp: int, success: bool, unlock_time: int = 0
):
    """
    Добавляет запись о попытке входа (успешной или неуспешной) в shared memory

    :param client_ip: IP-адрес
    :param username: Имя пользователя
    :param timestamp: Время попытки (unixtime)
    :param success: Флаг успешности попытки (True/False)
    :param unlock_time: Время разблокировки, если установлен бан (иначе 0)
    """
    shm, _ = initialize_auth_shm(False)
    if not shm or shm.buf is None:
        return
    packed = _pack_attempt_entry(client_ip, timestamp, username, success, unlock_time)
    entry_full_size = CONF["ENTRY_HEADER_SIZE"] + ENTRY_SIZE
    try:
        with LOCK:
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
        logger.error(f"Error writing to shared memory (auth attempts): {e}")


def get_auth_attempts_from_shm(since_time: int = 0) -> list:
    """
    Извлекает все попытки входа начиная с since_time

    :param since_time: Unixtime начала окна проверки
    :return: Список записей вида {"ip": str, "timestamp": int, "username": str}
    """
    shm, _ = initialize_auth_shm(False)
    if not shm or shm.buf is None:
        return []
    try:
        with LOCK:
            buf = shm.buf
            count = shm_read_int(buf, 0)
            next_idx = shm_read_int(buf, 4)
            num = min(int(count), int(CONF["MAX_BUFFER_SIZE"]))
            if num == 0:
                return []

            start_idx = (next_idx - num) % CONF["MAX_BUFFER_SIZE"]
            entry_full_size = CONF["ENTRY_HEADER_SIZE"] + ENTRY_SIZE

            attempts = []
            for i in range(num):
                idx = (start_idx + i) % CONF["MAX_BUFFER_SIZE"]
                offset = CONF["HEADER_SIZE"] + (idx * entry_full_size)
                data_size = shm_read_int(buf, offset)
                if data_size != ENTRY_SIZE:
                    continue
                packed = shm_read_bytes(
                    buf, offset + CONF["ENTRY_HEADER_SIZE"], ENTRY_SIZE
                )
                unpacked = ENTRY_STRUCT.unpack(packed)
                attempt = {
                    entry: unpacked[j].decode("utf-8", "ignore").rstrip(" ")
                    for j, entry in enumerate(CONF["ENTRY_ORDER"])
                }
                try:
                    attempt["timestamp"] = int(attempt["timestamp"])
                except Exception:
                    attempt["timestamp"] = 0
                attempts.append(attempt)
            if since_time:
                attempts = [a for a in attempts if a["timestamp"] >= since_time]
            return attempts
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory (auth attempts): {e}")
        raise e
