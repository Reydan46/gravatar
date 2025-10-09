import logging
import os
import struct
import tempfile
import time
from multiprocessing import shared_memory

from filelock import FileLock, Timeout

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def get_shared_lock_path(name: str) -> str:
    """
    Возвращает универсальный путь к lock-файлу в системной временной директории

    :param name: Имя блокируемого ресурса
    :return: Абсолютный путь к lock-файлу
    """
    tempdir = tempfile.gettempdir()
    return os.path.join(tempdir, f"{name}.lock")


def shm_initialize(
    name: str, size: int, create: bool = True, enable_logging: bool = True
) -> tuple[shared_memory.SharedMemory | None, bool]:
    """
    Инициализирует shared memory сегмент с использованием filelock для предотвращения гонок

    :param name: Имя сегмента
    :param size: Размер сегмента в байтах
    :param create: Создавать сегмент, если его нет
    :param enable_logging: Включает или отключает логирование внутри этой функции
    :return: (shm, is_creator)
    """
    lock_path = get_shared_lock_path(f'{name}.init')
    lock = FileLock(lock_path, timeout=1)

    for i in range(5):
        try:
            with lock:
                try:
                    shm = shared_memory.SharedMemory(name=name, create=False)
                    return shm, False
                except FileNotFoundError:
                    if not create:
                        return None, False
                    shm = shared_memory.SharedMemory(name=name, create=True, size=size)
                    if enable_logging:
                        logger.debug(f"Created shared memory for '{name}'")
                    return shm, True

        except Timeout:
            if enable_logging:
                logger.debug(
                    f"Waiting for lock on shared memory '{name}', attempt {i + 1}/5"
                )
            time.sleep(0.1)
            continue
        except ValueError as e:
            if enable_logging:
                logger.warning(f"Shared memory '{name}' might be corrupted: {e}")
            try:
                temp_memory = shared_memory.SharedMemory(name=name, create=False)
                temp_memory.close()
                temp_memory.unlink()
                if enable_logging:
                    logger.info(f"Removed corrupted shared memory '{name}'")
            except Exception as unlink_error:
                if enable_logging:
                    logger.error(
                        f"Failed to remove corrupted memory '{name}': {unlink_error}"
                    )
            time.sleep(0.2)
        except Exception as e:
            if enable_logging:
                logger.warning(
                    f"Error initializing shared memory '{name}': {type(e).__name__}: {e}"
                )
            time.sleep(0.2)

    if enable_logging:
        logger.error(
            f"Failed to initialize shared memory '{name}' after several retries"
        )
    return None, False


def shm_cleanup(shm: shared_memory.SharedMemory, is_creator: bool, name: str) -> None:
    """
    Очищает и удаляет shared memory сегмент

    :param shm: объект shared memory
    :param is_creator: был ли этот процесс создателем
    :param name: имя сегмента
    """
    logger.debug(
        f"[{'Creator' if is_creator else 'Worker'}] Cleaning up shared memory '{name}'"
    )
    try:
        shm.close()
        if is_creator:
            try:
                logger.debug(
                    f"[{'Creator' if is_creator else 'Worker'}] Unlinking shared memory '{name}'"
                )
                shm.unlink()
            except Exception as e:
                logger.error(f"Error unlinking shared memory '{name}': {e}")
    except Exception as e:
        logger.error(f"Error cleaning up shared memory '{name}': {e}")


def shm_write_int(buf, offset: int, value: int) -> None:
    """
    Записывает int в буфер (4 байта)

    :param buf: буфер
    :param offset: смещение
    :param value: значение
    """
    struct.pack_into("i", buf, offset, value)


def shm_read_int(buf, offset: int) -> int:
    """
    Читает int из буфера

    :param buf: буфер
    :param offset: смещение
    :return: значение
    """
    return struct.unpack_from("i", buf, offset)[0]


def shm_write_float(buf, offset: int, value: float) -> None:
    """
    Записывает float (8 байт, double) в буфер

    :param buf: буфер
    :param offset: смещение
    :param value: значение типа float
    """
    struct.pack_into("d", buf, offset, value)


def shm_read_float(buf, offset: int) -> float:
    """
    Читает float (8 байт, double) из буфера

    :param buf: буфер
    :param offset: смещение
    :return: считанное значение float
    """
    return struct.unpack_from("d", buf, offset)[0]


def shm_write_bytes(buf, offset: int, data: bytes) -> None:
    """
    Записывает произвольные байты в буфер

    :param buf: буфер
    :param offset: смещение
    :param data: данные для записи
    """
    buf[offset : offset + len(data)] = data


def shm_read_bytes(buf, offset: int, size: int) -> bytes:
    """
    Читает байты из буфера

    :param buf: буфер
    :param offset: смещение
    :param size: длина данных
    :return: считанные байты
    """
    return bytes(buf[offset : offset + size])


def shm_write_struct(buf, offset: int, fmt: str, *values):
    """
    Запись структуры в буфер

    :param buf: буфер
    :param offset: смещение
    :param fmt: формат struct (например 'I', 'ii', т.д.)
    :param values: значения для упаковки
    """
    struct.pack_into(fmt, buf, offset, *values)


def shm_read_struct(buf, offset: int, fmt: str):
    """
    Чтение структуры из буфера

    :param buf: буфер
    :param offset: смещение
    :param fmt: формат struct
    :return: распакованное значение(я)
    """
    return struct.unpack_from(fmt, buf, offset)


def _shorten_message(
    message: str, max_len: int, suffix: str = "... (truncated)"
) -> str:
    """
    Обрезает сообщение с добавлением суффикса "... (truncated)", если оно не помещается

    :param message: Исходное сообщение
    :param max_len: Максимально допустимая длина строки
    :param suffix: Суффикс
    :return: Обрезанное сообщение с суффиксом (если обрезано)
    """
    message_bytes = message.encode("utf-8")
    if len(message_bytes) <= max_len:
        return message
    encoded_suffix = suffix.encode("utf-8")
    available = max_len - len(encoded_suffix)
    if available <= 0:
        return suffix[:max_len]
    end = 0
    for idx, byte in enumerate(message_bytes):
        if idx >= available:
            break
        end = idx
    while end > 0 and (message_bytes[end] & 0b11000000) == 0b10000000:
        end -= 1
    short = message_bytes[:end].decode("utf-8", "ignore") + suffix
    return short
