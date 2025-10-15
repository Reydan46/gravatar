import base64
import logging
import os
from functools import lru_cache
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from filelock import FileLock

from config.constants import CRYPTO_MASTER_KEY_FILE, LOG_CONFIG
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


@lru_cache(maxsize=1)
def get_master_key() -> bytes:
    """
    Получает или генерирует мастер-ключ для шифрования.

    Ключ загружается из файла `crypto_master.key`. Если файл не существует,
    генерируется новый 256-битный ключ, сохраняется в файл и кешируется в памяти
    на уровне процесса с помощью декоратора lru_cache.
    Операции с файлом защищены блокировкой.

    :return: 32-байтовый мастер-ключ.
    """
    key_path = os.path.join(settings.internal_data_path, CRYPTO_MASTER_KEY_FILE)
    lock_path = f"{key_path}.lock"
    file_lock = FileLock(lock_path, timeout=5)

    with file_lock:
        if os.path.exists(key_path):
            try:
                with open(key_path, "rb") as f:
                    key = f.read()
                if len(key) == 32:
                    logger.debug("Loaded master key from file.")
                    return key
                else:
                    logger.warning(
                        "Master key file is corrupted (invalid length). A new key will be generated."
                    )
            except Exception as e:
                logger.error(f"Failed to read master key file: {e}")

        logger.info("Generating new master key.")
        new_key = os.urandom(32)
        try:
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(new_key)
            if os.name != "nt":
                os.chmod(key_path, 0o600)
            return new_key
        except Exception as e:
            logger.critical(f"Failed to save new master key: {e}")
            raise IOError("Could not create or save master key.") from e


def encrypt_payload(payload: bytes) -> str:
    """
    Шифрует данные с помощью мастер-ключа, используя AES-256-GCM.

    :param payload: Данные для шифрования (в байтах).
    :return: Строка в формате 'nonce_b64:ciphertext_b64'.
    """
    master_key = get_master_key()
    aesgcm = AESGCM(master_key)
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, payload, None)
    return f"{base64.b64encode(nonce).decode()}:{base64.b64encode(ciphertext).decode()}"


def decrypt_payload(encrypted_str: str) -> Optional[bytes]:
    """
    Расшифровывает данные, зашифрованные с помощью AES-256-GCM.

    :param encrypted_str: Строка в формате 'nonce_b64:ciphertext_b64'.
    :return: Расшифрованные данные (в байтах) или None при ошибке.
    """
    try:
        nonce_b64, ciphertext_b64 = encrypted_str.split(":", 1)
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)

        master_key = get_master_key()
        aesgcm = AESGCM(master_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        logger.error(f"Failed to decrypt payload: {e}")
        return None
