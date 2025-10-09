import logging
import struct
import time
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from filelock import FileLock, Timeout

from config.constants import LOG_CONFIG, SHARED_MEMORY_CONFIG
from shared_memory.shm_main import get_shared_lock_path, shm_initialize, shm_cleanup

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
CONF = SHARED_MEMORY_CONFIG["crypto"]

LOCK_PATH = get_shared_lock_path(CONF["MEMORY_NAME"])
LOCK = FileLock(LOCK_PATH, timeout=2)

STRUCT_FORMAT = "".join(
    (
        f'{CONF["ENTRY_SIZES"][entry]}s'
        if entry.endswith("_bytes")
        else ("d" if entry.endswith("time") else "I")
    )
    for entry in CONF["ENTRY_ORDER"]
)
ENTRY_STRUCT = struct.Struct(STRUCT_FORMAT)
ENTRY_SIZE = ENTRY_STRUCT.size
TOTAL_SIZE = ENTRY_SIZE


def initialize_crypto_shm(create: bool = True):
    """
    Инициализирует shared memory для одной пары ключей

    :param create: создавать ли сегмент
    :return: (shm, is_creator)
    """
    return shm_initialize(CONF["MEMORY_NAME"], TOTAL_SIZE, create)


def cleanup_crypto_shm(shm, is_creator: bool):
    """
    Очищает shared memory криптографии

    :param shm: Объект shared memory
    :param is_creator: Флаг - является ли процесс создателем памяти
    """
    shm_cleanup(shm, is_creator, CONF["MEMORY_NAME"])


def _pack_entry(
    private_key: RSAPrivateKey, public_key: RSAPublicKey, last_rotation: float
) -> bytes:
    """
    Упаковывает ключи и время ротации через struct

    :param private_key: приватный ключ
    :param public_key: публичный ключ
    :param last_rotation: время ротации
    :return: struct entry
    """
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    packed = ENTRY_STRUCT.pack(
        len(priv_bytes),
        len(pub_bytes),
        float(last_rotation),
        priv_bytes.ljust(CONF["ENTRY_SIZES"]["priv_bytes"], b"\x00"),
        pub_bytes.ljust(CONF["ENTRY_SIZES"]["pub_bytes"], b"\x00"),
    )
    return packed


def _unpack_entry(entry: bytes):
    """
    Распаковывает ключи и время ротации через struct

    :param entry: struct packed entry
    :return: (private_key, public_key, rot_time)
    """
    priv_len, pub_len, rot_time, priv_bytes, pub_bytes = ENTRY_STRUCT.unpack(entry)
    if priv_len == 0 or pub_len == 0:
        return None, None, None
    priv_bytes = priv_bytes[:priv_len]
    pub_bytes = pub_bytes[:pub_len]
    try:
        private_key = serialization.load_pem_private_key(
            priv_bytes, password=None, backend=default_backend()
        )
        public_key = serialization.load_pem_public_key(
            pub_bytes, backend=default_backend()
        )
    except Exception as e:
        logger.error(f"Failed to deserialize RSA keys from shared memory: {e}")
        return None, None, None
    return private_key, public_key, rot_time


def shm_crypto_set_keys(private_key: RSAPrivateKey, public_key: RSAPublicKey) -> None:
    """
    Сохраняет ключи и время ротации в shared memory с блокировкой

    :param private_key: Приватный ключ RSA
    :param public_key: Публичный ключ RSA
    :return: None
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    shm, _ = initialize_crypto_shm(False)
    if shm is None:
        return

    try:
        with LOCK:
            packed = _pack_entry(private_key, public_key, time.time())
            shm.buf[:ENTRY_SIZE] = packed
    except Timeout:
        logger.error("Timeout acquiring lock for writing to shared memory")
        raise TimeoutError("Timeout acquiring lock for writing to shared memory")
    except Exception as e:
        logger.error(f"Error writing to shared memory: {e}")


def shm_crypto_get_private_key() -> Optional[RSAPrivateKey]:
    """
    Читает приватный ключ из shared memory с блокировкой

    :return: Приватный ключ RSA или None
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    shm, _ = initialize_crypto_shm(False)
    if shm is None:
        return None
    try:
        with LOCK:
            entry = bytes(shm.buf[:ENTRY_SIZE])
            private_key, _, _ = _unpack_entry(entry)
            return private_key
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e


def shm_crypto_get_public_key() -> Optional[RSAPublicKey]:
    """
    Читает публичный ключ из shared memory с блокировкой

    :return: Публичный ключ RSA или None
    """
    shm, _ = initialize_crypto_shm(False)
    if shm is None:
        return None
    try:
        with LOCK:
            entry = bytes(shm.buf[:ENTRY_SIZE])
            _, public_key, _ = _unpack_entry(entry)
            return public_key
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e


def shm_crypto_get_last_rotation() -> Optional[float]:
    """
    Читает время последней ротации ключей из shared memory с блокировкой

    :return: Время ротации или None
    :raises TimeoutError: При невозможности захватить блокировку в течение timeout
    """
    shm, _ = initialize_crypto_shm(False)
    if shm is None:
        return None
    try:
        with LOCK:
            entry = bytes(shm.buf[:ENTRY_SIZE])
            _, _, rot_time = _unpack_entry(entry)
            return rot_time
    except Timeout:
        logger.error("Timeout acquiring lock for reading from shared memory")
        raise TimeoutError("Timeout acquiring lock for reading from shared memory")
    except Exception as e:
        logger.error(f"Error reading from shared memory: {e}")
        raise e
