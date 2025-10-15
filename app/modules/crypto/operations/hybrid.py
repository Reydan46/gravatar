import base64
import logging
import os
from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as symmetric_padding

from config.constants import CRYPTO_RSA_CONFIG, LOG_CONFIG
from modules.crypto.crypto_key_manager import (
    _get_hash_algorithm,
    get_mgf1_algorithm,
)
from shared_memory.shm_crypto import shm_crypto_get_private_key

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def _get_padding(cfg: Dict[str, str]) -> Any:
    """
    Формирует и возвращает объект паддинга для RSA в соответствии с заданными настройками

    :param cfg: Конфигурация с параметрами 'padding_mode', 'hash_algorithm', 'mgf1_hash', 'label'
    :return: Объект паддинга для использования при шифровании/расшифровке RSA
    """
    mode = cfg.get("padding_mode", "").upper()
    if mode == "OAEP":
        hash_obj = _get_hash_algorithm(cfg.get("hash_algorithm", "SHA256"))
        mgf1_algo = get_mgf1_algorithm(cfg)
        label = cfg.get("label", None)
        label_bytes = label.encode("utf-8") if isinstance(label, str) else None
        return padding.OAEP(
            mgf=padding.MGF1(algorithm=mgf1_algo), algorithm=hash_obj, label=label_bytes
        )
    elif mode == "PKCS1V15":
        return padding.PKCS1v15()
    else:
        logger.error(f"Unknown RSA padding mode: '{mode}'")
        raise Exception("Internal crypto error")


def _check_aes_key_iv(key: bytes, iv: bytes) -> None:
    """
    Проверяет корректность размера ключа и вектора инициализации для AES-CBC

    :param key: AES-ключ
    :param iv: Вектор инициализации
    :return: None
    """
    if len(key) != 32:
        logger.error(f"Invalid AES key: {len(key)}")
        raise Exception("Internal crypto error")
    if len(iv) != 16:
        logger.error(f"Invalid IV: {len(iv)}")
        raise Exception("Internal crypto error")


def decrypt(enc_data: str) -> str:
    """
    Расшифровывает зашифрованные данные с помощью приватного RSA-ключа из shared memory

    :param enc_data: Данные, зашифрованные RSA и закодированные в base64
    :return: Расшифрованная строка
    """
    private_key = shm_crypto_get_private_key()
    ciphertext = base64.b64decode(enc_data)
    pad_mode = _get_padding(CRYPTO_RSA_CONFIG)
    plaintext = private_key.decrypt(ciphertext, pad_mode)
    return plaintext.decode("utf-8")


def _get_decrypted_aes_key(enc_key: str) -> bytes:
    """
    Расшифровывает зашифрованный AES-ключ с помощью приватного RSA-ключа из shared memory, возвращает байтовое значение ключа

    :param enc_key: Зашифрованный AES-ключ в формате base64
    :return: Расшифрованный 32-байтовый AES-ключ (байты)
    """
    private_key = shm_crypto_get_private_key()
    symmetric_key_b64 = private_key.decrypt(
        base64.b64decode(enc_key), _get_padding(CRYPTO_RSA_CONFIG)
    )
    symmetric_key = base64.b64decode(symmetric_key_b64)
    if len(symmetric_key) != 32:
        logger.error(f"Decrypted AES key size invalid: {len(symmetric_key)} bytes")
        raise Exception("Internal crypto error")
    return symmetric_key


def _decrypt_aes_cbc(ciphertext_b64: str, key: bytes, iv: bytes) -> str:
    """
    Расшифровывает строку, зашифрованную с помощью AES в режиме CBC и PKCS7 паддингом

    :param ciphertext_b64: Зашифрованные данные в формате base64
    :param key: Байтовый симметричный ключ AES
    :param iv: Вектор инициализации (байты)
    :return: Открытая расшифрованная строка
    """
    _check_aes_key_iv(key, iv)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_plaintext = (
        decryptor.update(base64.b64decode(ciphertext_b64)) + decryptor.finalize()
    )
    unpadder = symmetric_padding.PKCS7(algorithms.AES.block_size).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    return plaintext.decode("utf-8")


def _encrypt_aes_cbc(plaintext: str, key: bytes, iv: bytes) -> str:
    """
    Шифрует строку с помощью AES (режим CBC, PKCS7 паддинг) и возвращает результат в формате base64

    :param plaintext: Исходная строка для шифрования
    :param key: Байтовый симметричный ключ AES
    :param iv: Вектор инициализации
    :return: Зашифрованная строка (base64)
    """
    _check_aes_key_iv(key, iv)
    padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    enc = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(enc).decode()


def decrypt_hybrid(payload: Dict[str, str]) -> str:
    """
    Выполняет гибридную (RSA+AES) расшифровку: расшифровывает AES-ключ, затем дешифрует сам payload

    :param payload: Словарь с ключами enc_key, enc_sym_data, iv (все строки base64)
    :return: Открытая строка после расшифровки
    """
    aes_key = _get_decrypted_aes_key(payload["enc_key"])
    iv = base64.b64decode(payload["iv"])
    return _decrypt_aes_cbc(payload["enc_sym_data"], aes_key, iv)


def encrypt_hybrid(payload: Dict[str, str], plaintext: str) -> Dict[str, str]:
    """
    Шифрует данные гибридным методом: расшифровывает AES-ключ, шифрует строку с помощью AES, возвращает словарь с результатом

    :param payload: Словарь, содержащий ключ enc_key (base64 зашифрованный AES-ключ)
    :param plaintext: Открытый текст для шифрования
    :return: Словарь с ключами enc_sym_data (base64 строка) и iv (base64)
    """
    aes_key = _get_decrypted_aes_key(payload["enc_key"])
    iv = os.urandom(16)
    enc_sym_data = _encrypt_aes_cbc(plaintext, aes_key, iv)
    return {"enc_sym_data": enc_sym_data, "iv": base64.b64encode(iv).decode()}
