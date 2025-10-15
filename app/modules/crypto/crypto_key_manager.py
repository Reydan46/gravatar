import logging
import time
from typing import Any, Dict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from config.constants import CRYPTO_RSA_CONFIG, LOG_CONFIG
from modules.crypto.crypto_storage import load_keys_from_disk, save_keys_to_disk
from shared_memory.shm_crypto import (
    shm_crypto_get_last_rotation,
    shm_crypto_set_keys,
)

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def _get_hash_algorithm(name: str) -> Any:
    """
    Возвращает объект хеш-алгоритма по заданному имени

    :param name: Имя хеш-алгоритма (например, 'SHA256')
    :return: Объект хеш-алгоритма для дальнейших криптографических операций
    """
    mapping = {
        "SHA256": hashes.SHA256,
        "SHA384": hashes.SHA384,
        "SHA512": hashes.SHA512,
        "SHA1": hashes.SHA1,
        "MD5": hashes.MD5,
    }
    algo_class = mapping.get(name.upper())
    if not algo_class:
        logger.error(f"Unknown hash algorithm requested: {name}")
        raise Exception("Internal crypto error")
    return algo_class()


def get_jwk_alg_from_crypto_conf(cfg: Dict[str, str]) -> str:
    """
    Определяет строку алгоритма ('alg') для JWK на основе переданных настроек

    :param cfg: Конфигурация, содержащая параметры padding_mode и hash_algorithm
    :return: Строка для поля 'alg' в JWK (например, 'RSA-OAEP-256')
    """
    pad = cfg.get("padding_mode", "").upper()
    hash_name = cfg.get("hash_algorithm", "SHA256").upper()
    if pad == "OAEP":
        if hash_name == "SHA256":
            return "RSA-OAEP-256"
        if hash_name == "SHA384":
            return "RSA-OAEP-384"
        if hash_name == "SHA512":
            return "RSA-OAEP-512"
        return "RSA-OAEP"
    elif pad == "PKCS1V15":
        return "RSA1_5"
    else:
        logger.warning(
            f"Unknown padding mode in crypto config: '{pad}', fallback to 'RSA'"
        )
        return "RSA"


def get_mgf1_algorithm(cfg: Dict[str, str]) -> Any:
    """
    Возвращает объект хеш-алгоритма для функции маскирования MGF1 по конфигурации

    :param cfg: Настройки, определяющие используемый хеш-алгоритм MGF1
    :return: Объект хеш-алгоритма MGF1
    """
    mgf_hash = cfg.get("mgf1_hash", cfg.get("hash_algorithm", "SHA256"))
    return _get_hash_algorithm(mgf_hash)


def refresh_keys(force: bool = False) -> None:
    """
    Проверяет и при необходимости обновляет пару RSA-ключей.

    Логика работы:
    1. Проверяет ключи в shared memory. Если они свежие, ничего не делает.
    2. Если в shared memory ключей нет, пытается загрузить их с диска.
    3. Если на диске есть свежие ключи, загружает их в shared memory.
    4. Если ключи требуют ротации (по времени или принудительно),
       генерирует новую пару, сохраняет на диск и в shared memory.

    :param force: Принудительно сгенерировать новую пару ключей.
    """
    # 1. Быстрая проверка в shared memory
    last_rotation_shm = shm_crypto_get_last_rotation()
    if (
        not force
        and last_rotation_shm is not None
        and (time.time() - last_rotation_shm)
        <= CRYPTO_RSA_CONFIG["key_rotation_period"]
    ):
        return

    # 2. Если SHM пуста или устарела, пытаемся загрузить с диска
    if not force:
        disk_keys = load_keys_from_disk()
        if disk_keys:
            private_key, public_key, created_at = disk_keys
            if (time.time() - created_at) <= CRYPTO_RSA_CONFIG["key_rotation_period"]:
                if last_rotation_shm != created_at:
                    logger.info("Loading RSA keys from disk into shared memory.")
                    shm_crypto_set_keys(private_key, public_key, created_at)
                return

    # 3. Если мы здесь, нужна генерация новых ключей
    rotation_reason = "Forced" if force else "Initial generation or rotation required"
    logger.info(f"Generating new RSA key pair: {rotation_reason}")
    try:
        private_key = rsa.generate_private_key(
            public_exponent=CRYPTO_RSA_CONFIG["public_exponent"],
            key_size=CRYPTO_RSA_CONFIG["key_size"],
        )
        public_key: RSAPublicKey = private_key.public_key()

        # 4. Сохраняем на диск, затем в shared memory
        saved_at = save_keys_to_disk(private_key, public_key)
        shm_crypto_set_keys(private_key, public_key, saved_at)

    except Exception as e:
        logger.critical(f"Failed to generate and persist RSA key pair: {type(e).__name__}: {e}")
        raise Exception("Internal crypto error") from e
