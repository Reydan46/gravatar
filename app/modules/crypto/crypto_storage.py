import json
import logging
import os
import time
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from filelock import FileLock

from config.constants import ENCRYPTED_RSA_KEY_FILE, LOG_CONFIG
from config.settings import settings
from modules.crypto.operations.symmetric import (
    decrypt_payload,
    encrypt_payload,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

ENCRYPTED_KEYS_PATH = os.path.join(settings.internal_data_path, ENCRYPTED_RSA_KEY_FILE)


def load_keys_from_disk() -> Optional[Tuple[RSAPrivateKey, RSAPublicKey, float]]:
    """
    Загружает и расшифровывает пару RSA-ключей с диска.

    Операция защищена файловой блокировкой для безопасности в многопроцессорной среде.

    :return: Кортеж (приватный ключ, публичный ключ, время создания) или None, если файл не найден или поврежден.
    """
    lock_path = f"{ENCRYPTED_KEYS_PATH}.lock"
    lock = FileLock(lock_path, timeout=5)

    with lock:
        if not os.path.exists(ENCRYPTED_KEYS_PATH):
            return None

        try:
            with open(ENCRYPTED_KEYS_PATH, "r") as f:
                encrypted_data = f.read()

            decrypted_bytes = decrypt_payload(encrypted_data)
            if not decrypted_bytes:
                logger.error("Failed to decrypt key file. It might be corrupted.")
                return None

            key_data = json.loads(decrypted_bytes.decode())
            private_key = serialization.load_pem_private_key(
                key_data["private_key"].encode(), password=None
            )
            public_key = serialization.load_pem_public_key(
                key_data["public_key"].encode()
            )
            created_at = float(key_data["created_at"])
            logger.info("Successfully loaded RSA key pair from disk.")
            return private_key, public_key, created_at
        except (FileNotFoundError, json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Error loading keys from disk: {e}")
            return None


def save_keys_to_disk(private_key: RSAPrivateKey, public_key: RSAPublicKey) -> float:
    """
    Шифрует и сохраняет пару RSA-ключей на диск.

    Операция защищена файловой блокировкой для безопасности в многопроцессорной среде.

    :param private_key: Приватный ключ RSA.
    :param public_key: Публичный ключ RSA.
    :return: Время сохранения ключей (timestamp).
    :raises IOError: Если не удалось сохранить файл.
    """
    created_at = time.time()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    key_data = {
        "private_key": private_pem,
        "public_key": public_pem,
        "created_at": created_at,
    }
    payload_bytes = json.dumps(key_data).encode()
    encrypted_data = encrypt_payload(payload_bytes)

    lock_path = f"{ENCRYPTED_KEYS_PATH}.lock"
    lock = FileLock(lock_path, timeout=5)

    with lock:
        try:
            os.makedirs(os.path.dirname(ENCRYPTED_KEYS_PATH), exist_ok=True)
            with open(ENCRYPTED_KEYS_PATH, "w") as f:
                f.write(encrypted_data)
            if os.name != "nt":
                os.chmod(ENCRYPTED_KEYS_PATH, 0o600)
            logger.info("New RSA key pair securely saved to disk.")
        except Exception as e:
            logger.critical(f"Failed to save encrypted keys to disk: {e}")
            raise IOError("Could not save key file.") from e

    return created_at
