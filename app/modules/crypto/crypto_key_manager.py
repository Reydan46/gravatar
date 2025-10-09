import logging
import time
from typing import Any, Dict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from config.constants import CRYPTO_RSA_CONFIG, LOG_CONFIG
from shared_memory.shm_crypto import (
    shm_crypto_get_last_rotation,
    shm_crypto_get_private_key,
    shm_crypto_get_public_key,
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
    Выполняет проверку необходимости ротации ключей RSA и, в случае необходимости, генерирует новую пару

    :param force: Принудительно ротация ключей при True
    :return: None
    """
    private_key = shm_crypto_get_private_key()
    public_key = shm_crypto_get_public_key()
    last_rotation = shm_crypto_get_last_rotation()
    rotation_needed = False
    rotation_reason = ""

    if force:
        rotation_needed = True
        rotation_reason = "Forced keypair generation"
    elif not private_key or not public_key or not last_rotation:
        rotation_needed = True
        rotation_reason = "Initial keypair generation"
    elif (time.time() - last_rotation) > CRYPTO_RSA_CONFIG["key_rotation_period"]:
        rotation_needed = True
        rotation_reason = "Keypair rotated by time limit"

    if not rotation_needed:
        return

    logger.info(f"Generating RSA keypair: {rotation_reason}")
    try:
        private_key = rsa.generate_private_key(
            public_exponent=CRYPTO_RSA_CONFIG["public_exponent"],
            key_size=CRYPTO_RSA_CONFIG["key_size"],
        )
        public_key = private_key.public_key()
        shm_crypto_set_keys(private_key, public_key)
    except Exception as e:
        logger.critical(f"Failed to generate RSA keypair: {type(e).__name__}: {e}")
        raise Exception("Internal crypto error")
